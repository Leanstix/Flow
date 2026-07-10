from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Notification
from .serializers import NotificationSerializer


def notification_group_name(user_id):
    return f'notifications_user_{user_id}'


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
    broadcast_notification(notification)
    return notification


def broadcast_notification(notification):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    payload = NotificationSerializer(notification).data
    async_to_sync(channel_layer.group_send)(
        notification_group_name(notification.recipient_id),
        {
            'type': 'notification.created',
            'notification': payload,
        },
    )
