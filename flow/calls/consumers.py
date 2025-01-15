import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.exceptions import StopConsumer

class CallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            async def connect(self):
                self.room_name = self.scope['url_route']['kwargs']['room_name']
                self.room_group_name = f'call_{self.room_name}'

                await self.channel_layer.group_add(
                    self.room_group_name,
                    self.channel_name
                )
                await self.accept()
        except Exception as e:
            await self.close()

    async def disconnect(self, close_code):
        try:
            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        except Exception as e:
            pass  # Log the error if necessary

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            event_type = data.get('type')
            if not event_type:
                await self.send_error("Missing 'type' in message data.")
                return

            # Relay the message to all participants in the group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'call_message',
                    'event_type': event_type,
                    'data': data
                }
            )
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format.")
        except Exception as e:
            await self.send_error("An error occurred while processing the message.")

    async def call_message(self, event):
        try:
            # Send the message to WebSocket client
            await self.send(text_data=json.dumps({
                'event_type': event['event_type'],
                'data': event['data']
            }))
        except Exception as e:
            await self.send_error("Failed to send message.")

    async def send_error(self, message):
        """Send an error message to the WebSocket client."""
        await self.send(text_data=json.dumps({
            'error': message
        }))