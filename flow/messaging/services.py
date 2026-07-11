from decimal import Decimal

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.db.models import Count
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from flow.media import (
    AUDIO_TYPES,
    DOCUMENT_TYPES,
    IMAGE_TYPES,
    VIDEO_TYPES,
    store_upload,
    validate_upload,
)
from notifications.models import Notification
from notifications.services import create_notification

from .models import Conversation, Message, MessageAttachment, MessageReceipt
from .serializers import MessageSerializer


ATTACHMENT_LIMITS = {
    MessageAttachment.Kind.IMAGE: (IMAGE_TYPES, 12 * 1024 * 1024, 10),
    MessageAttachment.Kind.VIDEO: (VIDEO_TYPES, 100 * 1024 * 1024, 1),
    MessageAttachment.Kind.AUDIO: (AUDIO_TYPES, 25 * 1024 * 1024, 1),
    MessageAttachment.Kind.DOCUMENT: (DOCUMENT_TYPES, 25 * 1024 * 1024, 10),
}


def conversation_group_name(conversation_id):
    return f'conversation_{conversation_id}'


def hydrated_message(message_or_id):
    message_id = message_or_id.pk if hasattr(message_or_id, 'pk') else message_or_id
    return Message.objects.select_related(
        'conversation', 'sender', 'reply_to', 'reply_to__sender'
    ).prefetch_related(
        'receipts', 'attachments', 'reply_to__attachments'
    ).get(pk=message_id)


def serialize_message(message, request=None):
    return MessageSerializer(hydrated_message(message), context={'request': request}).data


def get_or_create_direct_conversation(first_user, second_user):
    participant_ids = {first_user.id, second_user.id}
    candidates = Conversation.objects.annotate(
        participant_count=Count('participants')
    ).filter(
        participant_count=2,
        participants__id__in=participant_ids,
    ).distinct()
    for conversation in candidates:
        if set(conversation.participants.values_list('id', flat=True)) == participant_ids:
            return conversation, False
    conversation = Conversation.objects.create()
    conversation.participants.set(participant_ids)
    return conversation, True


def ensure_message_receipts(message):
    recipient_ids = message.conversation.participants.exclude(id=message.sender_id).values_list('id', flat=True)
    MessageReceipt.objects.bulk_create(
        [MessageReceipt(message=message, user_id=user_id) for user_id in recipient_ids],
        ignore_conflicts=True,
    )


def create_message_attachments(message, request, attachment_data):
    kind = attachment_data.get('attachment_type')
    payload = attachment_data.get('attachment_payload') or {}
    declared_duration = attachment_data.get('attachment_duration_seconds')
    uploads = list(request.FILES.getlist('files')) if request else list(attachment_data.get('files') or [])
    if not kind:
        return []

    if kind in {
        MessageAttachment.Kind.CONTACT,
        MessageAttachment.Kind.LOCATION,
        MessageAttachment.Kind.LISTING,
    }:
        return [MessageAttachment.objects.create(
            message=message,
            kind=kind,
            metadata=payload,
        )]

    allowed_types, max_bytes, max_count = ATTACHMENT_LIMITS[kind]
    if len(uploads) > max_count:
        raise ValidationError({'files': f'You can attach at most {max_count} {kind} file(s) per message.'})

    created = []
    for position, upload in enumerate(uploads):
        mime_type = validate_upload(
            upload,
            allowed_types=allowed_types,
            max_bytes=max_bytes,
            label=kind.title(),
        )
        stored_kind = 'document' if kind == MessageAttachment.Kind.DOCUMENT else kind
        stored = store_upload(
            upload,
            folder=f'flow/messages/{kind}',
            kind=stored_kind,
            declared_duration_seconds=declared_duration,
        )
        if kind == MessageAttachment.Kind.VIDEO and stored.get('duration_seconds') and float(stored['duration_seconds']) > 180:
            raise ValidationError({'files': 'Message videos must be 3 minutes or shorter.'})
        created.append(MessageAttachment.objects.create(
            message=message,
            kind=kind,
            url=stored.get('url') or '',
            thumbnail_url=stored.get('thumbnail_url') or '',
            public_id=stored.get('public_id') or '',
            file_name=stored.get('file_name') or getattr(upload, 'name', ''),
            mime_type=stored.get('mime_type') or mime_type,
            size_bytes=stored.get('size_bytes') or 0,
            duration_seconds=Decimal(str(stored['duration_seconds'])) if stored.get('duration_seconds') is not None else None,
            metadata=payload,
            position=position,
        ))
    return created


def create_message_with_attachments(
    *,
    conversation,
    sender,
    content='',
    reply_to=None,
    request=None,
    attachment_data=None,
):
    attachment_data = attachment_data or {}
    with transaction.atomic():
        message = Message.objects.create(
            conversation=conversation,
            sender=sender,
            content=(content or '').strip(),
            reply_to=reply_to,
        )
        create_message_attachments(message, request, attachment_data)
        ensure_message_receipts(message)
        create_message_notifications(message)
        transaction.on_commit(lambda: broadcast_message(message))
    return hydrated_message(message)


def _group_send(conversation_id, payload):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    async_to_sync(channel_layer.group_send)(conversation_group_name(conversation_id), payload)


def broadcast_message(message):
    payload = serialize_message(message)
    _group_send(message.conversation_id, {'type': 'chat.message', 'message': payload})


def broadcast_message_updated(message):
    payload = serialize_message(message)
    _group_send(message.conversation_id, {'type': 'chat.message_updated', 'message': payload})


def broadcast_message_deleted(message):
    payload = serialize_message(message)
    _group_send(message.conversation_id, {'type': 'chat.message_deleted', 'message': payload})


def broadcast_receipt_status(message):
    payload = serialize_message(message)
    _group_send(
        message.conversation_id,
        {
            'type': 'chat.receipt',
            'message_id': payload['id'],
            'status': payload['status'],
            'recipient_count': payload['recipient_count'],
            'delivered_count': payload['delivered_count'],
            'read_count': payload['read_count'],
            'is_read': payload['is_read'],
        },
    )


def mark_conversation_delivered(conversation, user):
    now = timezone.now()
    with transaction.atomic():
        receipts = MessageReceipt.objects.select_for_update().filter(
            user=user,
            message__conversation=conversation,
            delivered_at__isnull=True,
        )
        message_ids = list(receipts.values_list('message_id', flat=True).distinct())
        updated_count = receipts.update(delivered_at=now)
        transaction.on_commit(lambda: [broadcast_receipt_status(message_id) for message_id in message_ids])
    return updated_count


def mark_conversation_read(conversation, user):
    now = timezone.now()
    with transaction.atomic():
        receipts = MessageReceipt.objects.select_for_update().filter(
            user=user,
            message__conversation=conversation,
            read_at__isnull=True,
        )
        message_ids = list(receipts.values_list('message_id', flat=True).distinct())
        updated_count = receipts.update(delivered_at=now, read_at=now)

        for message_id in message_ids:
            if not MessageReceipt.objects.filter(message_id=message_id, read_at__isnull=True).exists():
                Message.objects.filter(pk=message_id).update(is_read=True)

        transaction.on_commit(lambda: [broadcast_receipt_status(message_id) for message_id in message_ids])
    return updated_count


def create_message_notifications(message):
    recipients = message.conversation.participants.exclude(id=message.sender_id)
    actor_label = message.sender.user_name or message.sender.email
    attachment_label = message.attachments.first().get_kind_display().lower() if message.attachments.exists() else None
    notification_text = (
        f'{actor_label} sent you a {attachment_label}.'
        if attachment_label and not message.content
        else f'{actor_label} sent you a message.'
    )
    for recipient in recipients:
        create_notification(
            recipient=recipient,
            actor=message.sender,
            verb=Notification.Verb.MESSAGE,
            message=notification_text,
            target_conversation=message.conversation,
        )
