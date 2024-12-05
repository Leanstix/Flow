from rest_framework import serializers
from .models import Message, Conversation
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email']

class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender', 'content', 'timestamp', 'is_read']

    def create(self, validated_data):
        request = self.context.get('request')
        if request:
            validated_data['sender'] = request.user  # Automatically set the sender to the logged-in user
        return super().create(validated_data)

class ConversationSerializer(serializers.ModelSerializer):
    participants = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.all()
    )

    class Meta:
        model = Conversation
        fields = ['id', 'participants', 'created_at']

    def to_representation(self, instance):
        """Override to return full user data for participants"""
        representation = super().to_representation(instance)
        representation['participants'] = UserSerializer(instance.participants, many=True).data
        return representation
