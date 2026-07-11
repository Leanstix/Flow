from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import CallInvitation, Room

User = get_user_model()


class CallUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'user_name', 'profile_picture']


class CallInvitationSerializer(serializers.ModelSerializer):
    user = CallUserSerializer(read_only=True)
    invited_by = CallUserSerializer(read_only=True)

    class Meta:
        model = CallInvitation
        fields = ['id', 'user', 'invited_by', 'status', 'created_at', 'responded_at']


class RoomSerializer(serializers.ModelSerializer):
    created_by = CallUserSerializer(read_only=True)
    participants = CallUserSerializer(many=True, read_only=True)
    invitations = CallInvitationSerializer(many=True, read_only=True)
    conversation_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Room
        fields = [
            'id',
            'room_name',
            'created_by',
            'conversation_id',
            'call_type',
            'status',
            'participants',
            'invitations',
            'created_at',
            'started_at',
            'ended_at',
        ]
