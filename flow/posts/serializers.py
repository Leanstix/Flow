from rest_framework import serializers
from .models import Post, Comment, Like, Report

# Comment Serializer
class CommentSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()  # To fetch specific user details
    likes_count = serializers.ReadOnlyField()
    comments_count = serializers.ReadOnlyField()


    class Meta:
        model = Comment
        fields = [
            "id",
            "user",
            "content",
            "created_at",
            "likes_count",
            "comments_count",
        ]

    def get_user(self, obj):
        user = obj.user
        return {
            "id": user.id,
            "username": user.user_name,
            "email": user.email,  # Add any other fields you want to include
        } 

# Post Serializer
class PostSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source="user.username")
    likes_count = serializers.ReadOnlyField()
    comments_count = serializers.ReadOnlyField()

    class Meta:
        model = Post
        fields = ["id", "user", "content", "created_at", "likes_count", "comments_count"]

# Like Serializer (Not strictly necessary for the API but useful for API responses)
class LikeSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()  # To fetch detailed user info

    class Meta:
        model = Like
        fields = ["id", "user", "post"]

    def get_user(self, obj):
        return {
            "id": obj.user.id,
            "username": obj.user.user_name,
        }

# Report Serializer
class ReportSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = ["id", "user", "post", "reason", "created_at"]

    def get_user(self, obj):
        return {
            "id": obj.user.id,
            "username": obj.user.user_name,
        }
