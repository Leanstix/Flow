from rest_framework import serializers

from .models import Comment, Like, Post, Report


def user_payload(user):
    return {
        "id": user.id,
        "username": user.user_name,
        "email": user.email,
    }


class CommentSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    post = serializers.IntegerField(source="post_id", read_only=True)
    parent = serializers.IntegerField(source="parent_id", read_only=True)
    replies_count = serializers.ReadOnlyField()

    class Meta:
        model = Comment
        fields = [
            "id",
            "post",
            "parent",
            "user",
            "content",
            "created_at",
            "replies_count",
        ]
        read_only_fields = ["id", "post", "parent", "user", "created_at", "replies_count"]

    def validate_content(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Comment content cannot be empty.")
        return value.strip()

    def get_user(self, obj):
        return user_payload(obj.user)


class PostSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    likes_count = serializers.ReadOnlyField()
    comments_count = serializers.ReadOnlyField()
    reposts_count = serializers.ReadOnlyField()
    has_liked = serializers.SerializerMethodField()
    reposted_from = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id",
            "user",
            "content",
            "created_at",
            "reposted_from",
            "likes_count",
            "comments_count",
            "reposts_count",
            "has_liked",
        ]
        read_only_fields = ["id", "user", "created_at", "likes_count", "comments_count", "reposts_count", "has_liked", "reposted_from"]

    def validate_content(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Post content cannot be empty.")
        return value.strip()

    def get_user(self, obj):
        return user_payload(obj.user)

    def get_has_liked(self, obj):
        request = self.context.get("request")
        if not request or not request.user or request.user.is_anonymous:
            return False
        return obj.likes.filter(user=request.user).exists()

    def get_reposted_from(self, obj):
        if not obj.reposted_from:
            return None
        original = obj.reposted_from
        return {
            "id": original.id,
            "user": user_payload(original.user),
            "content": original.content,
            "created_at": original.created_at,
        }


class LikeSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = Like
        fields = ["id", "user", "post", "created_at"]
        read_only_fields = ["id", "user", "created_at"]

    def get_user(self, obj):
        return user_payload(obj.user)


class ReportSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = Report
        fields = ["id", "user", "post", "reason", "created_at"]
        read_only_fields = ["id", "user", "created_at"]

    def get_user(self, obj):
        return user_payload(obj.user)
