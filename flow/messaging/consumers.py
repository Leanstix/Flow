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

        message_content = content.get('content', '')
        if not isinstance(message_content, str) or not message_content.strip():
            await self.send_json({'type': 'error', 'error': 'Message content cannot be empty.'})
            return

        message = await self.create_message(message_content.strip())
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
    def create_message(self, content):
        from .models import Conversation, Message
        from .services import create_message_notifications, serialize_message

        conversation = Conversation.objects.get(id=self.conversation_id)
        message = Message.objects.create(conversation=conversation, sender=self.user, content=content)
        create_message_notifications(message)
        return serialize_message(message)
