from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from flow.asgi import application
from notifications.models import Notification

from .models import Conversation, Message

User = get_user_model()

TEST_CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}


class MessagingApiTests(APITestCase):
    def setUp(self):
        self.alice = User.objects.create_user(
            email='alice@example.com',
            university_id='ALICE001',
            password='pass12345',
            user_name='alice',
            is_active=True,
        )
        self.bob = User.objects.create_user(
            email='bob@example.com',
            university_id='BOB001',
            password='pass12345',
            user_name='bob',
            is_active=True,
        )
        self.mallory = User.objects.create_user(
            email='mallory@example.com',
            university_id='MALL001',
            password='pass12345',
            user_name='mallory',
            is_active=True,
        )
        self.client.force_authenticate(self.alice)

    def test_create_conversation_accepts_other_participant_only_and_reuses_duplicate(self):
        response = self.client.post(
            reverse('conversation-list'),
            {'participants': [self.bob.id]},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        conversation_id = response.data['id']
        self.assertEqual(Conversation.objects.get(id=conversation_id).participants.count(), 2)

        duplicate_response = self.client.post(
            reverse('conversation-list'),
            {'participants': [self.bob.id]},
            format='json',
        )

        self.assertEqual(duplicate_response.status_code, status.HTTP_200_OK)
        self.assertEqual(duplicate_response.data['id'], conversation_id)

    def test_message_queryset_is_limited_to_conversation_participants(self):
        conversation = Conversation.objects.create()
        conversation.participants.set([self.alice, self.bob])
        message = Message.objects.create(conversation=conversation, sender=self.alice, content='hello')

        self.client.force_authenticate(self.mallory)
        response = self.client.get(reverse('message-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'] if isinstance(response.data, dict) and 'results' in response.data else response.data, [])

        create_response = self.client.post(
            reverse('message-list'),
            {'conversation': conversation.id, 'content': 'intrusion'},
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Message.objects.filter(id=message.id).count(), 1)

    def test_send_message_creates_notification_for_other_participants(self):
        conversation = Conversation.objects.create()
        conversation.participants.set([self.alice, self.bob])

        response = self.client.post(
            reverse('conversation-send-message', kwargs={'pk': conversation.id}),
            {'content': 'Hello Bob'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Message.objects.filter(conversation=conversation, sender=self.alice).count(), 1)
        self.assertEqual(
            Notification.objects.filter(recipient=self.bob, actor=self.alice, verb=Notification.Verb.MESSAGE).count(),
            1,
        )

    def test_mark_read_marks_only_other_users_messages(self):
        conversation = Conversation.objects.create()
        conversation.participants.set([self.alice, self.bob])
        Message.objects.create(conversation=conversation, sender=self.bob, content='unread')
        own_message = Message.objects.create(conversation=conversation, sender=self.alice, content='own unread')

        response = self.client.post(reverse('conversation-mark-read', kwargs={'pk': conversation.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['updated_count'], 1)
        own_message.refresh_from_db()
        self.assertFalse(own_message.is_read)


@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS)
class MessagingWebsocketTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.alice = User.objects.create_user(
            email='ws-alice@example.com',
            university_id='WSA001',
            password='pass12345',
            user_name='wsalice',
            is_active=True,
        )
        self.bob = User.objects.create_user(
            email='ws-bob@example.com',
            university_id='WSB001',
            password='pass12345',
            user_name='wsbob',
            is_active=True,
        )
        self.conversation = Conversation.objects.create()
        self.conversation.participants.set([self.alice, self.bob])

    def test_websocket_sends_message_and_creates_notification(self):
        async_to_sync(self._websocket_sends_message_and_creates_notification)()

    async def _websocket_sends_message_and_creates_notification(self):
        token = str(AccessToken.for_user(self.alice))
        communicator = WebsocketCommunicator(
            application,
            f'/ws/conversations/{self.conversation.id}/?token={token}',
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        await communicator.send_json_to({'content': 'Realtime hello'})
        response = await communicator.receive_json_from()

        self.assertEqual(response['type'], 'message.created')
        self.assertEqual(response['message']['content'], 'Realtime hello')

        await communicator.disconnect()

        self.assertEqual(await self._message_count(), 1)
        self.assertEqual(await self._notification_count(), 1)

    @async_to_sync
    async def noop(self):
        pass

    @staticmethod
    @async_to_sync
    async def _unused():
        return None

    @staticmethod
    def _sync_count(model, **filters):
        return model.objects.filter(**filters).count()

    @database_sync_to_async
    def _message_count(self):
        return Message.objects.filter(conversation=self.conversation, sender=self.alice, content='Realtime hello').count()

    @database_sync_to_async
    def _notification_count(self):
        return Notification.objects.filter(recipient=self.bob, actor=self.alice, verb=Notification.Verb.MESSAGE).count()
