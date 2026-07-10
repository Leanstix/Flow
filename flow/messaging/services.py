from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from notifications.models import Notification
from notifications.services import create_notification

from .serializers import MessageSerializer


def conversation_group_name(conversation_id):
    return f'conversation_{conversation_id}'


def serialize_message(message):
    return MessageSerializer(message).data


def broadcast_message(message):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    async_to_sync(channel_layer.group_send)(
        conversation_group_name(message.conversation_id),
        {
            'type': 'chat.message',
            'message': serialize_message(message),
        },
    )


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
