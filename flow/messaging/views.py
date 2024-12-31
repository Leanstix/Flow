from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.contrib.auth import get_user_model
from django.db.models import Count
from .models import Message, Conversation
from .serializers import MessageSerializer, ConversationSerializer
from rest_framework.exceptions import ValidationError

User = get_user_model()

class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Conversation.objects.none()
        return Conversation.objects.filter(participants=self.request.user)

    def get_serializer_context(self):
        """Provide context to the serializer"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def create(self, request, *args, **kwargs):
        participants = request.data.get('participants')

        # Validate participants
        if not participants or len(participants) != 2:
            return Response(
                {"error": "A conversation must include exactly two participants."},
                status=status.HTTP_400_BAD_REQUEST
            )

        participants_set = {request.user.id, *map(int, participants)}  # Include the current user and ensure IDs are integers

        if len(participants_set) != 2:
            return Response(
                {"error": "A conversation must include exactly two distinct participants."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Check for an existing conversation with exactly these two participants
            existing_conversation = Conversation.objects.annotate(
                participant_count=Count('participants')
            ).filter(
                participant_count=2,
                participants__id__in=participants_set
            ).distinct()

            for conversation in existing_conversation:
                if set(conversation.participants.values_list('id', flat=True)) == participants_set:
                    # Return the existing conversation
                    return Response(
                        self.get_serializer(conversation).data,
                        status=status.HTTP_200_OK
                    )

            # If no existing conversation, create a new one
            conversation = Conversation.objects.create()
            conversation.participants.set(participants_set)
            return Response(
                self.get_serializer(conversation).data,
                status=status.HTTP_201_CREATED
            )

        except User.DoesNotExist:
            return Response(
                {"error": "One or more participants do not exist."},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        conversation = self.get_object()
        messages = Message.objects.filter(conversation=conversation).order_by('-timestamp')[:50]
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        conversation = self.get_object()
        content = request.data.get('content')

        if not content:
            return Response(
                {"error": "Message content cannot be empty."},
                status=status.HTTP_400_BAD_REQUEST
            )

        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=content
        )
        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)


class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        conversation_id = self.request.data.get('conversation')

        if not conversation_id:
            raise serializers.ValidationError({"conversation": "This field is required."})

        try:
            conversation = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            raise serializers.ValidationError({"conversation": "Invalid conversation ID."})

        # Ensure sender is a participant in the conversation
        if self.request.user not in conversation.participants.all():
            raise serializers.ValidationError({"sender": "You are not a participant in this conversation."})

        serializer.save(sender=self.request.user, conversation=conversation)
