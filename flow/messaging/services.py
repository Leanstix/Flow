from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.utils import timezone

from notifications.models import Notification
from notifications.services import create_notification

from .models import Message, MessageReceipt
from .serializers import MessageSerializer


def conversation_group_name(conversation_id):
    return f'conversation_{conversation_id}'


def hydrated_message(message_or_id):
    message_id = message_or_id.pk if hasattr(message_or_id, 'pk') else message_or_id
    return Message.objects.select_related(
        'conversation', 'sender', 'reply_to', 'reply_to__sender'
    ).prefetch_related('receipts').get(pk=message_id)


def serialize_message(message):
    return MessageSerializer(hydrated_message(message)).data


def ensure_message_receipts(message):
    recipient_ids = message.conversation.participants.exclude(id=message.sender_id).values_list('id', flat=True)
    MessageReceipt.objects.bulk_create(
        [MessageReceipt(message=message, user_id=user_id) for user_id in recipient_ids],
        ignore_conflicts=True,
    )


def _group_send(conversation_id, payload):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    async_to_sync(channel_layer.group_send)(conversation_group_name(conversation_id), payload)


def broadcast_message(message):
    payload = serialize_message(message)
    _group_send(
        message.conversation_id,
        {'type': 'chat.message', 'message': payload},
    )


def broadcast_message_updated(message):
    payload = serialize_message(message)
    _group_send(
        message.conversation_id,
        {'type': 'chat.message_updated', 'message': payload},
    )


def broadcast_message_deleted(message):
    payload = serialize_message(message)
    _group_send(
        message.conversation_id,
        {'type': 'chat.message_deleted', 'message': payload},
    )


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
        transaction.on_commit(
            lambda: [broadcast_receipt_status(message_id) for message_id in message_ids]
        )
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
            unread_receipts_exist = MessageReceipt.objects.filter(
                message_id=message_id,
                read_at__isnull=True,
            ).exists()
            if not unread_receipts_exist:
                Message.objects.filter(pk=message_id).update(is_read=True)

        transaction.on_commit(
            lambda: [broadcast_receipt_status(message_id) for message_id in message_ids]
        )
    return updated_count


def create_message_notifications(message):
    recipients = message.conversation.participants.exclude(id=message.sender_id)
    actor_label = message.sender.user_name or message.sender.email
    for recipient in recipients:
        create_notification(
            recipient=recipient,
            actor=message.sender,
            verb=Notification.Verb.MESSAGE,
            message=f'{actor_label} sent you a message.',
            target_conversation=message.conversation,
        )
