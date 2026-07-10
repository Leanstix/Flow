from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .services import conversation_group_name


class ConversationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get('user')
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.group_name = conversation_group_name(self.conversation_id)

        if not self.user or self.user.is_anonymous:
            await self.close(code=4401)
            return

        if not await self.is_participant():
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.mark_delivered()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        event_type = content.get('type', 'message')

        if event_type == 'typing':
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'chat.typing',
                    'user_id': self.user.id,
                    'user_name': self.user.user_name,
                },
            )
            return

        if event_type == 'read':
            await self.mark_read()
            return

        message_content = content.get('content', '')
        if not isinstance(message_content, str) or not message_content.strip():
            await self.send_json({'type': 'error', 'error': 'Message content cannot be empty.'})
            return

        reply_to = content.get('reply_to')
        try:
            reply_to = int(reply_to) if reply_to not in (None, '') else None
        except (TypeError, ValueError):
            await self.send_json({'type': 'error', 'error': 'reply_to must be a valid message id.'})
            return

        try:
            message = await self.create_message(message_content.strip(), reply_to)
        except ValueError as exc:
            await self.send_json({'type': 'error', 'error': str(exc)})
            return

        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'chat.message',
                'message': message,
            },
        )

    async def chat_message(self, event):
        await self.send_json({
            'type': 'message.created',
            'message': event['message'],
        })

    async def chat_message_updated(self, event):
        await self.send_json({
            'type': 'message.updated',
            'message': event['message'],
        })

    async def chat_message_deleted(self, event):
        await self.send_json({
            'type': 'message.deleted',
            'message': event['message'],
        })

    async def chat_receipt(self, event):
        await self.send_json({
            'type': 'message.receipt',
            'message_id': event['message_id'],
            'status': event['status'],
            'recipient_count': event['recipient_count'],
            'delivered_count': event['delivered_count'],
            'read_count': event['read_count'],
            'is_read': event['is_read'],
        })

    async def chat_typing(self, event):
        if event['user_id'] == self.user.id:
            return
        await self.send_json({
            'type': 'typing',
            'user_id': event['user_id'],
            'user_name': event.get('user_name'),
        })

    @database_sync_to_async
    def is_participant(self):
        from .models import Conversation

        return Conversation.objects.filter(id=self.conversation_id, participants=self.user).exists()

    @database_sync_to_async
    def mark_delivered(self):
        from .models import Conversation
        from .services import mark_conversation_delivered

        conversation = Conversation.objects.get(id=self.conversation_id)
        return mark_conversation_delivered(conversation, self.user)

    @database_sync_to_async
    def mark_read(self):
        from .models import Conversation
        from .services import mark_conversation_read

        conversation = Conversation.objects.get(id=self.conversation_id)
        return mark_conversation_read(conversation, self.user)

    @database_sync_to_async
    def create_message(self, content, reply_to_id=None):
        from django.db import transaction

        from .models import Conversation, Message
        from .services import create_message_notifications, ensure_message_receipts, serialize_message

        conversation = Conversation.objects.get(id=self.conversation_id)
        reply_to = None
        if reply_to_id is not None:
            reply_to = Message.objects.filter(id=reply_to_id, conversation=conversation).first()
            if not reply_to:
                raise ValueError('Replies must reference a message in the same conversation.')

        with transaction.atomic():
            message = Message.objects.create(
                conversation=conversation,
                sender=self.user,
                content=content,
                reply_to=reply_to,
            )
            ensure_message_receipts(message)
            create_message_notifications(message)
        return serialize_message(message)
