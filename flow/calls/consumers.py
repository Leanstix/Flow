import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .services import room_call_group, user_call_group

logger = logging.getLogger(__name__)


class UserCallConsumer(AsyncJsonWebsocketConsumer):
    """Private per-user channel for incoming call invitations and lifecycle updates."""

    async def connect(self):
        self.user = self.scope.get('user')
        if not self.user or self.user.is_anonymous:
            await self.close(code=4401)
            return
        self.group_name = user_call_group(self.user.id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def call_event(self, event):
        await self.send_json({
            'type': event['event_type'],
            'call': event['call'],
            **{key: value for key, value in event.items() if key not in {'type', 'event_type', 'call'}},
        })


class CallConsumer(AsyncJsonWebsocketConsumer):
    ALLOWED_EVENT_TYPES = {
        'ready',
        'offer',
        'answer',
        'ice-candidate',
        'new-ice-candidate',
        'hangup',
        'media-state',
        'network-quality',
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

        self.room_group_name = room_call_group(self.room_name)
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        event_type = content.get('type')
        if event_type not in self.ALLOWED_EVENT_TYPES:
            await self.send_json({'type': 'error', 'error': 'Unsupported or missing call signalling type.'})
            return

        if event_type == 'new-ice-candidate':
            event_type = 'ice-candidate'
            content = {**content, 'type': event_type}

        target_id = content.get('target_id')
        if target_id not in (None, ''):
            try:
                target_id = int(target_id)
            except (TypeError, ValueError):
                await self.send_json({'type': 'error', 'error': 'target_id must be a valid user id.'})
                return
            if target_id == self.user.id or not await self.is_room_participant_id(target_id):
                await self.send_json({'type': 'error', 'error': 'The signalling target is not in this call.'})
                return

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'call.message',
                'event_type': event_type,
                'sender_channel': self.channel_name,
                'sender_id': self.user.id,
                'sender_name': self.user.user_name or self.user.email,
                'target_id': target_id,
                'data': content,
            },
        )

    async def call_message(self, event):
        if event['sender_channel'] == self.channel_name:
            return
        if event.get('target_id') and event['target_id'] != self.user.id:
            return
        await self.send_json({
            'event_type': event['event_type'],
            'sender_id': event['sender_id'],
            'sender_name': event.get('sender_name'),
            'target_id': event.get('target_id'),
            'data': event['data'],
        })

    async def call_state(self, event):
        await self.send_json({
            'event_type': event['event_type'],
            'call': event['call'],
            **{key: value for key, value in event.items() if key not in {'type', 'event_type', 'call'}},
        })

    @database_sync_to_async
    def is_room_participant(self):
        from .models import Room
        return Room.objects.filter(
            room_name=self.room_name,
            participants=self.user,
            status__in=['ringing', 'active'],
        ).exists()

    @database_sync_to_async
    def is_room_participant_id(self, user_id):
        from .models import Room
        return Room.objects.filter(
            room_name=self.room_name,
            participants__id=user_id,
            status__in=['ringing', 'active'],
        ).exists()
