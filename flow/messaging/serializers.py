from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Conversation, Message, MessageAttachment

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'user_name', 'profile_picture']


def absolute_url(request, value):
    if not value:
        return ''
    if value.startswith(('http://', 'https://')) or not request:
        return value
    return request.build_absolute_uri(value)


class MessageAttachmentSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()

    class Meta:
        model = MessageAttachment
        fields = [
            'id', 'kind', 'url', 'thumbnail_url', 'file_name', 'mime_type',
            'size_bytes', 'duration_seconds', 'metadata', 'position', 'created_at',
        ]
        read_only_fields = fields

    def get_url(self, obj):
        return absolute_url(self.context.get('request'), obj.url)

    def get_thumbnail_url(self, obj):
        return absolute_url(self.context.get('request'), obj.thumbnail_url)


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
    attachments = MessageAttachmentSerializer(many=True, read_only=True)
    attachment_type = serializers.ChoiceField(
        choices=MessageAttachment.Kind.choices,
        required=False,
        write_only=True,
    )
    attachment_payload = serializers.JSONField(required=False, write_only=True)
    attachment_duration_seconds = serializers.FloatField(required=False, write_only=True, min_value=0)
    files = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        write_only=True,
        max_length=10,
    )

    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'content', 'timestamp', 'reply_to',
            'reply_preview', 'edited_at', 'deleted_at', 'is_deleted', 'status',
            'recipient_count', 'delivered_count', 'read_count', 'is_read',
            'attachments', 'attachment_type', 'attachment_payload',
            'attachment_duration_seconds', 'files',
        ]
        read_only_fields = [
            'id', 'sender', 'timestamp', 'reply_preview', 'edited_at',
            'deleted_at', 'is_deleted', 'status', 'recipient_count',
            'delivered_count', 'read_count', 'is_read', 'attachments',
        ]
        extra_kwargs = {'content': {'required': False, 'allow_blank': True}}

    def validate_content(self, value):
        value = (value or '').strip()
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

        request = self.context.get('request')
        uploads = list(request.FILES.getlist('files')) if request else list(attrs.get('files') or [])
        attachment_type = attrs.get('attachment_type')
        attachment_payload = attrs.get('attachment_payload')
        content = attrs.get('content', getattr(instance, 'content', '') if instance else '')

        if not instance and not content and not uploads and not attachment_payload:
            raise serializers.ValidationError({'content': 'Write a message or attach something.'})
        if uploads and not attachment_type:
            raise serializers.ValidationError({'attachment_type': 'Choose what type of file you are attaching.'})
        if attachment_type in {
            MessageAttachment.Kind.CONTACT,
            MessageAttachment.Kind.LOCATION,
            MessageAttachment.Kind.LISTING,
        } and not attachment_payload:
            raise serializers.ValidationError({'attachment_payload': 'Attachment details are required.'})
        if attachment_type in {
            MessageAttachment.Kind.IMAGE,
            MessageAttachment.Kind.VIDEO,
            MessageAttachment.Kind.AUDIO,
            MessageAttachment.Kind.DOCUMENT,
        } and not uploads:
            raise serializers.ValidationError({'files': 'Choose at least one file.'})
        return attrs

    def create(self, validated_data):
        for field in ('attachment_type', 'attachment_payload', 'attachment_duration_seconds', 'files'):
            validated_data.pop(field, None)
        return super().create(validated_data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.deleted_at:
            data['content'] = ''
            data['attachments'] = []
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
            'attachments': [] if replied.deleted_at else MessageAttachmentSerializer(
                replied.attachments.all(),
                many=True,
                context=self.context,
            ).data,
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
        last_message = obj.messages.select_related(
            'sender', 'reply_to', 'reply_to__sender'
        ).prefetch_related('receipts', 'attachments', 'reply_to__attachments').order_by('-timestamp').first()
        if not last_message:
            return None
        return MessageSerializer(last_message, context=self.context).data

    def get_unread_count(self, obj):
        request = self.context.get('request')
        if not request or not request.user or request.user.is_anonymous:
            return 0
        return obj.messages.filter(receipts__user=request.user, receipts__read_at__isnull=True).distinct().count()
