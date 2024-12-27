from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import FriendRequest
from messaging.models import Conversation  # Import Conversation model
from django.db.models import Q
from django.db import models

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    is_friends = serializers.SerializerMethodField()
    conversation_id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "user_name", "email", "first_name", "last_name", "is_friends", "conversation_id"]

    def get_is_friends(self, obj):
        request = self.context.get("request")
        if not request:
            return False

        user = request.user
        is_friend = User.objects.filter(
            (Q(sent_requests__to_user=user, sent_requests__accepted=True) & Q(id=obj.id)) |
            (Q(received_requests__from_user=user, received_requests__accepted=True) & Q(id=obj.id))
        ).exists()

        return is_friend

    def get_conversation_id(self, obj):
        request = self.context.get("request")
        if not request:
            return None

        user = request.user

        print(f"User: {user}, Friend: {obj}")  # Debug users
        
        conversations = Conversation.objects.filter(participants__in=[user, obj])
        print(f"Conversations with participants: {conversations}")  # Debug intermediate query

        conversation = (
            conversations.annotate(participant_count=models.Count("participants"))
            .filter(participant_count=2)
            .first()
        )

        print(f"Final Conversation: {conversation}")  # Debug final result

        return conversation.id if conversation else None
    
class FriendRequestSerializer(serializers.ModelSerializer):
    from_user = UserSerializer()
    to_user = UserSerializer()

    class Meta:
        model = FriendRequest
        fields = ["id", "from_user", "to_user", "timestamp", "accepted"]

class FriendSerializer(serializers.ModelSerializer):
    conversation_id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "user_name", "email", "first_name", "last_name", "conversation_id"]

    def get_conversation_id(self, obj):
        request = self.context.get("request")
        if not request:
            return None

        user = request.user
        # Query for conversations where both users are participants
        conversation = (
            Conversation.objects.filter(participants__in=[user, obj])
            .annotate(participant_count=models.Count("participants"))
            .filter(participant_count=2)
            .first()
        )
        return conversation.id if conversation else None
    