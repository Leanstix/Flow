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
    participants = UserSerializer(many=True, read_only=True)
    name = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'participants', 'created_at', 'name', 'last_message']

    def get_name(self, obj):
        request_user = self.context['request'].user
        participants = obj.participants.exclude(id=request_user.id)  # Exclude the requesting user
        if participants.count() == 1:  # Check if there's exactly one other participant
            return participants.first().user_name
        return "Group Conversation"

    def get_last_message(self, obj):
        last_message = obj.messages.order_by('-timestamp').first()  # Get the latest message
        if last_message:
            return {
                'id': last_message.id,
                'sender': last_message.sender.user_name,
                'content': last_message.content,
                'timestamp': last_message.timestamp
            }
        return None  # Return None if there are no messages

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['name'] = self.get_name(instance)  # Add the dynamic name field
        representation['last_message'] = self.get_last_message(instance)  # Add the last message field
        return representation