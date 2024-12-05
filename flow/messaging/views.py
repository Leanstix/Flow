from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.contrib.auth import get_user_model
from .models import Message, Conversation
from .serializers import MessageSerializer, ConversationSerializer

User = get_user_model()

class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Conversation.objects.none()
        return Conversation.objects.filter(participants=self.request.user)

    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        conversation = self.get_object()
        content = request.data.get('content')
        if not content:
            return Response(
                {"error": "Content cannot be empty"},
                status=status.HTTP_400_BAD_REQUEST
            )

        message = Message(
            conversation=conversation,
            sender=request.user,
            content=content
        )
        message.save()
        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)

class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        conversation_id = self.request.data.get('conversation')  # Get conversation ID from the request
        if not conversation_id:
            raise serializers.ValidationError({"conversation": "This field is required."})
        
        try:
            conversation = Conversation.objects.get(id=conversation_id)
        except Conversation.DoesNotExist:
            raise serializers.ValidationError({"conversation": "Invalid conversation ID."})
        
        serializer.save(sender=self.request.user, conversation=conversation)
