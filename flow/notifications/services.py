from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

from .models import Notification
from .serializers import NotificationSerializer


def notification_group_name(user_id):
    if not user_id:
        raise ValueError('A recipient user id is required for notification delivery.')
    return f'notifications_user_{int(user_id)}'


def create_notification(*, recipient, actor=None, verb=Notification.Verb.SYSTEM, message='', target_post=None, target_comment=None, target_conversation=None):
    if recipient is None:
        return None
    if actor is not None and actor.pk == recipient.pk:
        return None

    notification = Notification.objects.create(
        recipient=recipient,
        actor=actor,
        verb=verb,
        message=message,
        target_post=target_post,
        target_comment=target_comment,
        target_conversation=target_conversation,
    )
    transaction.on_commit(lambda: broadcast_notification(notification.pk, notification.recipient_id))
    return notification


def broadcast_notification(notification_id, recipient_id):
    """Broadcast one notification only to its persisted recipient.

    The notification is loaded again after the surrounding transaction commits so
    a stale in-memory object or caller-provided payload can never choose the socket
    group. The database recipient is the source of truth.
    """

    try:
        notification = Notification.objects.select_related(
            'actor', 'target_post', 'target_comment', 'target_conversation'
        ).get(pk=notification_id, recipient_id=recipient_id)
    except Notification.DoesNotExist:
        return

    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    payload = NotificationSerializer(notification).data
    async_to_sync(channel_layer.group_send)(
        notification_group_name(notification.recipient_id),
        {
            'type': 'notification.created',
            'recipient_id': notification.recipient_id,
            'notification': payload,
        },
    )
