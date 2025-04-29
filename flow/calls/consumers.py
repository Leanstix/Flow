import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.exceptions import StopConsumer


class CallConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """
        Handles a WebSocket connection request.
        """
        self.room_name = self.scope['url_route']['kwargs'].get('room_name')
        if not self.room_name:
            await self.close()
            return

        self.room_group_name = f'call_{self.room_name}'

        try:
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()
        except Exception as e:
            await self.log_error("Error during connection", e)
            await self.close()

    async def disconnect(self, close_code):
        """
        Handles a WebSocket disconnection.
        """
        try:
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
        except Exception as e:
            await self.log_error("Error during disconnection", e)

    async def receive(self, text_data):
        """
        Handles messages received from the WebSocket client.
        """
        try:
            data = self.parse_json(text_data)
            if not data:
                return

            event_type = data.get('type')
            if not event_type:
                await self.send_error("Missing 'type' in message data.")
                return

            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'call_message',
                    'event_type': event_type,
                    'sender_channel': self.channel_name,
                    'data': data
                }
            )
        except Exception as e:
            await self.log_error("Error during message reception", e)

    async def call_message(self, event):
        """
        Handles messages broadcast to the group and relays them to the client.
        """
        if event['sender_channel'] == self.channel_name:
            return

        try:
            await self.send(text_data=json.dumps({
                'event_type': event['event_type'],
                'data': event['data']
            }))
        except Exception as e:
            await self.log_error("Failed to send message", e)

    async def send_error(self, message):
        """
        Sends an error message to the WebSocket client.
        """
        await self.send(text_data=json.dumps({'error': message}))

    def parse_json(self, text_data):
        """
        Safely parses JSON data and handles errors.
        """
        try:
            return json.loads(text_data)
        except json.JSONDecodeError:
            self.send_error("Invalid JSON format.")
            return None

    async def log_error(self, context, exception):
        """
        Logs an error message and optionally sends it to the client.
        """
        # Replace with actual logging if needed
        print(f"{context}: {str(exception)}")
