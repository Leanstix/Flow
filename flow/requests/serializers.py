from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import FriendRequest

# Dynamically retrieve the custom user model
User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        # Ensure these fields match your custom user model
        fields = ["id", "user_name", "email", "first_name", "last_name"]

class FriendRequestSerializer(serializers.ModelSerializer):
    from_user = UserSerializer()
    to_user = UserSerializer()

    class Meta:
        model = FriendRequest
        fields = ["id", "from_user", "to_user", "timestamp", "accepted"]

class FriendSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        # Adjust fields based on your custom user model
        fields = ["id", "user_name", "email", "first_name", "last_name"]