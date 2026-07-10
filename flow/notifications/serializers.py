from rest_framework import serializers

from .models import Notification


class NotificationUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    user_name = serializers.CharField(allow_blank=True, allow_null=True)


class NotificationSerializer(serializers.ModelSerializer):
    actor = serializers.SerializerMethodField()
    target_post_id = serializers.IntegerField(source='target_post.id', read_only=True)
    target_comment_id = serializers.IntegerField(source='target_comment.id', read_only=True)
    target_conversation_id = serializers.IntegerField(source='target_conversation.id', read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id',
            'recipient',
            'actor',
            'verb',
            'message',
            'target_post_id',
            'target_comment_id',
            'target_conversation_id',
            'is_read',
            'created_at',
        ]
        read_only_fields = fields

    def get_actor(self, obj):
        if not obj.actor:
            return None
        return {
            'id': obj.actor.id,
            'email': obj.actor.email,
            'user_name': obj.actor.user_name,
        }
