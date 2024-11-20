from rest_framework import serializers
from .models import Post

class PostSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source="user.username")

    class Meta:
        model = Post
        fields = ["id", "user", "content", "created_at"]