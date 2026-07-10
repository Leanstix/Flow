from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer


class CallConsumer(AsyncJsonWebsocketConsumer):
    ALLOWED_EVENT_TYPES = {
        'ready',
        'offer',
        'answer',
        'new-ice-candidate',
        'hangup',
    }

    async def connect(self):
        self.user = self.scope.get('user')
        self.room_name = self.scope['url_route']['kwargs'].get('room_name')

        if not self.user or self.user.is_anonymous:
            await self.close(code=4401)
            return
        if not self.room_name or not await self.is_room_participant():
            await self.close(code=4403)
            return

        self.room_group_name = f'call_{self.room_name}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        event_type = content.get('type')
        if event_type not in self.ALLOWED_EVENT_TYPES:
            await self.send_json({
                'type': 'error',
                'error': 'Unsupported or missing call signalling type.',
            })
            return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'call.message',
                'event_type': event_type,
                'sender_channel': self.channel_name,
                'sender_id': self.user.id,
                'data': content,
            },
        )

    async def call_message(self, event):
        if event['sender_channel'] == self.channel_name:
            return
        await self.send_json({
            'event_type': event['event_type'],
            'sender_id': event['sender_id'],
            'data': event['data'],
        })

    @database_sync_to_async
    def is_room_participant(self):
        from .models import Room

        return Room.objects.filter(
            room_name=self.room_name,
            participants=self.user,
        ).exists()
