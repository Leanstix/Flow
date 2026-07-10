from django.contrib.auth import get_user_model
from django.db.models import Count
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer
from .services import broadcast_message, create_message_notifications

User = get_user_model()


class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Conversation.objects.none()
        return Conversation.objects.filter(participants=self.request.user).prefetch_related('participants', 'messages')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def create(self, request, *args, **kwargs):
        participant_ids = request.data.get('participants')
        if not isinstance(participant_ids, list) or not participant_ids:
            return Response(
                {'error': 'participants must be a non-empty list of user ids.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            participants_set = {int(user_id) for user_id in participant_ids}
        except (TypeError, ValueError):
            return Response(
                {'error': 'participants must contain only valid user ids.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        participants_set.add(request.user.id)
        if len(participants_set) < 2:
            return Response(
                {'error': 'A conversation must include at least two distinct participants.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing_users = set(User.objects.filter(id__in=participants_set).values_list('id', flat=True))
        missing_users = participants_set - existing_users
        if missing_users:
            return Response(
                {'error': 'One or more participants do not exist.', 'missing_user_ids': sorted(missing_users)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(participants_set) == 2:
            existing_conversations = Conversation.objects.annotate(
                participant_count=Count('participants')
            ).filter(
                participant_count=2,
                participants__id__in=participants_set,
            ).distinct()

            for conversation in existing_conversations:
                if set(conversation.participants.values_list('id', flat=True)) == participants_set:
                    return Response(self.get_serializer(conversation).data, status=status.HTTP_200_OK)

        conversation = Conversation.objects.create()
        conversation.participants.set(participants_set)
        return Response(self.get_serializer(conversation).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        conversation = self.get_object()
        recent_messages = list(
            Message.objects.filter(conversation=conversation)
            .select_related('sender')
            .order_by('-timestamp')[:50]
        )
        serializer = MessageSerializer(reversed(recent_messages), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        conversation = self.get_object()
        serializer = MessageSerializer(data={**request.data, 'conversation': conversation.id})
        serializer.is_valid(raise_exception=True)
        message = serializer.save(conversation=conversation, sender=request.user)
        broadcast_message(message)
        create_message_notifications(message)
        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        conversation = self.get_object()
        updated_count = conversation.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
        return Response({'updated_count': updated_count}, status=status.HTTP_200_OK)


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Message.objects.none()
        return Message.objects.filter(conversation__participants=self.request.user).select_related('sender', 'conversation')

    def perform_create(self, serializer):
        conversation_id = self.request.data.get('conversation')
        if not conversation_id:
            raise serializers.ValidationError({'conversation': 'This field is required.'})

        try:
            conversation = Conversation.objects.get(id=conversation_id, participants=self.request.user)
        except Conversation.DoesNotExist:
            raise ValidationError({'conversation': 'Invalid conversation ID or you are not a participant.'})

        message = serializer.save(sender=self.request.user, conversation=conversation)
        broadcast_message(message)
        create_message_notifications(message)
