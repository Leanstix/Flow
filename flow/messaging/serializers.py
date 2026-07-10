from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Conversation, Message

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'user_name']


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender', 'content', 'timestamp', 'is_read']
        read_only_fields = ['id', 'sender', 'timestamp', 'is_read']

    def validate_content(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Message content cannot be empty.')
        return value.strip()


class ConversationSerializer(serializers.ModelSerializer):
    participants = UserSerializer(many=True, read_only=True)
    name = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'participants', 'created_at', 'name', 'last_message', 'unread_count']

    def get_name(self, obj):
        request = self.context.get('request')
        if not request or not request.user or request.user.is_anonymous:
            return 'Conversation'

        participants = obj.participants.exclude(id=request.user.id)
        if participants.count() == 1:
            user = participants.first()
            return user.user_name or user.email
        return 'Group Conversation'

    def get_last_message(self, obj):
        last_message = obj.messages.select_related('sender').order_by('-timestamp').first()
        if not last_message:
            return None
        return MessageSerializer(last_message).data

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if not request or not request.user or request.user.is_anonymous:
            return 0
        return obj.messages.filter(is_read=False).exclude(sender=request.user).count()
