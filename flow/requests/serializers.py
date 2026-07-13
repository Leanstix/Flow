from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q
from rest_framework import serializers

from messaging.models import Conversation

from .models import FriendRequest

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    is_friends = serializers.SerializerMethodField()
    conversation_id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'user_name',
            'email',
            'first_name',
            'last_name',
            'profile_picture',
            'is_friends',
            'conversation_id',
        ]

    def get_is_friends(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False

        user = request.user
        return User.objects.filter(
            (
                Q(sent_requests__to_user=user, sent_requests__accepted=True)
                | Q(received_requests__from_user=user, received_requests__accepted=True)
            )
            & Q(id=obj.id)
        ).exists()

    def get_conversation_id(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous or self.context.get('mention_context'):
            return None

        conversation = (
            Conversation.objects.filter(participants=request.user)
            .filter(participants=obj)
            .annotate(participant_count=models.Count('participants'))
            .filter(participant_count=2)
            .first()
        )
        return conversation.id if conversation else None


class FriendRequestSerializer(serializers.ModelSerializer):
    from_user = UserSerializer()
    to_user = UserSerializer()

    class Meta:
        model = FriendRequest
        fields = ['id', 'from_user', 'to_user', 'timestamp', 'accepted']


class FriendSerializer(serializers.ModelSerializer):
    conversation_id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'user_name',
            'email',
            'first_name',
            'last_name',
            'profile_picture',
            'conversation_id',
        ]

    def get_conversation_id(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return None

        conversation = (
            Conversation.objects.filter(participants=request.user)
            .filter(participants=obj)
            .annotate(participant_count=models.Count('participants'))
            .filter(participant_count=2)
            .first()
        )
        return conversation.id if conversation else None
