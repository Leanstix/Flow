from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Conversation, Message

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'user_name', 'profile_picture']


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    reply_to = serializers.PrimaryKeyRelatedField(
        queryset=Message.objects.all(),
        required=False,
        allow_null=True,
    )
    reply_preview = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    delivered_count = serializers.SerializerMethodField()
    read_count = serializers.SerializerMethodField()
    recipient_count = serializers.SerializerMethodField()
    is_read = serializers.SerializerMethodField()
    is_deleted = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id',
            'conversation',
            'sender',
            'content',
            'timestamp',
            'reply_to',
            'reply_preview',
            'edited_at',
            'deleted_at',
            'is_deleted',
            'status',
            'recipient_count',
            'delivered_count',
            'read_count',
            'is_read',
        ]
        read_only_fields = [
            'id',
            'sender',
            'timestamp',
            'reply_preview',
            'edited_at',
            'deleted_at',
            'is_deleted',
            'status',
            'recipient_count',
            'delivered_count',
            'read_count',
            'is_read',
        ]

    def validate_content(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Message content cannot be empty.')
        value = value.strip()
        if len(value) > 5000:
            raise serializers.ValidationError('Message content cannot exceed 5000 characters.')
        return value

    def validate(self, attrs):
        instance = getattr(self, 'instance', None)
        if instance and instance.deleted_at:
            raise serializers.ValidationError({'detail': 'Deleted messages cannot be edited.'})

        conversation = attrs.get('conversation') or getattr(instance, 'conversation', None)
        reply_to = attrs.get('reply_to')
        if reply_to and conversation and reply_to.conversation_id != conversation.id:
            raise serializers.ValidationError({'reply_to': 'Replies must reference a message in the same conversation.'})
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.deleted_at:
            data['content'] = ''
        return data

    def _receipt_stats(self, obj):
        cached = getattr(obj, '_receipt_stats_cache', None)
        if cached is not None:
            return cached

        receipts = list(obj.receipts.all())
        total = len(receipts)
        delivered = sum(1 for receipt in receipts if receipt.delivered_at)
        read = sum(1 for receipt in receipts if receipt.read_at)
        if total > 0 and read == total:
            status = 'read'
        elif total > 0 and delivered == total:
            status = 'delivered'
        else:
            status = 'sent'

        cached = {
            'status': status,
            'recipient_count': total,
            'delivered_count': delivered,
            'read_count': read,
        }
        obj._receipt_stats_cache = cached
        return cached

    def get_reply_preview(self, obj):
        replied = obj.reply_to
        if not replied:
            return None
        return {
            'id': replied.id,
            'sender': UserSerializer(replied.sender).data,
            'content': '' if replied.deleted_at else replied.content,
            'is_deleted': bool(replied.deleted_at),
        }

    def get_status(self, obj):
        return self._receipt_stats(obj)['status']

    def get_recipient_count(self, obj):
        return self._receipt_stats(obj)['recipient_count']

    def get_delivered_count(self, obj):
        return self._receipt_stats(obj)['delivered_count']

    def get_read_count(self, obj):
        return self._receipt_stats(obj)['read_count']

    def get_is_read(self, obj):
        return self._receipt_stats(obj)['status'] == 'read'

    def get_is_deleted(self, obj):
        return bool(obj.deleted_at)


class MessageEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['content']

    def validate_content(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('Message content cannot be empty.')
        value = value.strip()
        if len(value) > 5000:
            raise serializers.ValidationError('Message content cannot exceed 5000 characters.')
        return value


class ConversationSerializer(serializers.ModelSerializer):
    participants = UserSerializer(many=True, read_only=True)
    name = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'participants', 'created_at', 'name', 'last_message', 'unread_count']

    def get_name(self, obj):
        request = self.context.get('request')
        if not request or not request.user or request.user.is_anonymous:
            return 'Conversation'

        participants = obj.participants.exclude(id=request.user.id)
        if participants.count() == 1:
            user = participants.first()
            return user.user_name or user.email
        return 'Group Conversation'

    def get_last_message(self, obj):
        last_message = obj.messages.select_related('sender', 'reply_to', 'reply_to__sender').prefetch_related('receipts').order_by('-timestamp').first()
        if not last_message:
            return None
        return MessageSerializer(last_message).data

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if not request or not request.user or request.user.is_anonymous:
            return 0
        return obj.messages.filter(receipts__user=request.user, receipts__read_at__isnull=True).distinct().count()
