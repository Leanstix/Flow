from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Room

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class RoomSerializer(serializers.ModelSerializer):
    participants = UserSerializer(many=True, read_only=True)  # Nested serialization

    class Meta:
        model = Room
        fields = ['id', 'room_name', 'created_at', 'participants']
