import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.exceptions import StopConsumer

class CallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """
        Handles a WebSocket connection request.
        """
        try:
            self.room_name = self.scope['url_route']['kwargs']['room_name']
            self.room_group_name = f'call_{self.room_name}'

            # Add this connection to the channel group
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()
        except Exception as e:
            # Log the error if necessary
            await self.close()

    async def disconnect(self, close_code):
        """
        Handles a WebSocket disconnection.
        """
        try:
            # Remove this connection from the channel group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        except Exception as e:
            # Log the error if necessary
            pass  # Avoid raising errors during disconnect

    async def receive(self, text_data):
        """
        Handles messages received from the WebSocket client.
        """
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
                    'sender_channel': self.channel_name,
                    'data': data
                }
            )
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format.")
        except Exception as e:
            await self.send_error(f"An error occurred: {str(e)}")

    async def call_message(self, event):
        """
        Handles messages broadcast to the group and relays them to the client.
        """
        try:
            if event['sender_channel'] != self.channel_name:
                await self.send(text_data=json.dumps({
                    'event_type': event['event_type'],
                    'data': event['data']
                }))
        except Exception as e:
            await self.send_error(f"Failed to send message: {str(e)}")

    async def send_error(self, message):
        """
        Sends an error message to the WebSocket client.
        """
        await self.send(text_data=json.dumps({
            'error': message
        }))
