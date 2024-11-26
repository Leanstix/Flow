from rest_framework import serializers
from django.contrib.auth.models import User
from .models import FriendRequest

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name"]

class FriendRequestSerializer(serializers.ModelSerializer):
    from_user = UserSerializer()
    to_user = UserSerializer()

    class Meta:
        model = FriendRequest
        fields = ["id", "from_user", "to_user", "timestamp", "accepted"]