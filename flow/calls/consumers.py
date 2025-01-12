# consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class CallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'call_{self.room_name}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        event_type = data.get('type')

        # Relay the message to all participants in the group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'call_message',
                'event_type': event_type,
                'data': data
            }
        )

    async def call_message(self, event):
        # Send the message to WebSocket client
        await self.send(text_data=json.dumps({
            'event_type': event['event_type'],
            'data': event['data']
        }))
