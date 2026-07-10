from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from flow.asgi import application
from notifications.models import Notification

from .models import Conversation, Message, MessageReceipt
from .services import ensure_message_receipts

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
        self.conversation = Conversation.objects.create()
        self.conversation.participants.set([self.alice, self.bob])

    def create_message(self, sender=None, content='hello', conversation=None):
        message = Message.objects.create(
            conversation=conversation or self.conversation,
            sender=sender or self.alice,
            content=content,
        )
        ensure_message_receipts(message)
        return message

    def test_create_conversation_accepts_other_participant_only_and_reuses_duplicate(self):
        Conversation.objects.all().delete()
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
        message = self.create_message()

        self.client.force_authenticate(self.mallory)
        response = self.client.get(reverse('message-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_payload = response.data['results'] if isinstance(response.data, dict) and 'results' in response.data else response.data
        self.assertEqual(response_payload, [])

        create_response = self.client.post(
            reverse('message-list'),
            {'conversation': self.conversation.id, 'content': 'intrusion'},
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Message.objects.filter(id=message.id).count(), 1)

    def test_send_message_creates_receipt_and_notification_for_other_participants(self):
        response = self.client.post(
            reverse('conversation-send-message', kwargs={'pk': self.conversation.id}),
            {'content': 'Hello Bob'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        message = Message.objects.get(id=response.data['id'])
        self.assertEqual(MessageReceipt.objects.filter(message=message, user=self.bob).count(), 1)
        self.assertEqual(response.data['status'], 'sent')
        self.assertEqual(
            Notification.objects.filter(recipient=self.bob, actor=self.alice, verb=Notification.Verb.MESSAGE).count(),
            1,
        )

    def test_reply_must_reference_same_conversation(self):
        original = self.create_message(content='Original')
        response = self.client.post(
            reverse('conversation-send-message', kwargs={'pk': self.conversation.id}),
            {'content': 'Reply', 'reply_to': original.id},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['reply_to'], original.id)
        self.assertEqual(response.data['reply_preview']['content'], 'Original')

        other_conversation = Conversation.objects.create()
        other_conversation.participants.set([self.alice, self.mallory])
        foreign = self.create_message(conversation=other_conversation, content='Foreign')
        rejected = self.client.post(
            reverse('conversation-send-message', kwargs={'pk': self.conversation.id}),
            {'content': 'Invalid reply', 'reply_to': foreign.id},
            format='json',
        )
        self.assertEqual(rejected.status_code, status.HTTP_400_BAD_REQUEST)

    def test_sender_can_edit_and_soft_delete_message(self):
        message = self.create_message(content='Before edit')
        edit_response = self.client.patch(
            reverse('message-detail', kwargs={'pk': message.id}),
            {'content': 'After edit'},
            format='json',
        )
        self.assertEqual(edit_response.status_code, status.HTTP_200_OK)
        self.assertEqual(edit_response.data['content'], 'After edit')
        self.assertIsNotNone(edit_response.data['edited_at'])

        delete_response = self.client.delete(reverse('message-detail', kwargs={'pk': message.id}))
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        message.refresh_from_db()
        self.assertIsNotNone(message.deleted_at)

        retrieve_response = self.client.get(reverse('message-detail', kwargs={'pk': message.id}))
        self.assertEqual(retrieve_response.status_code, status.HTTP_200_OK)
        self.assertEqual(retrieve_response.data['content'], '')
        self.assertTrue(retrieve_response.data['is_deleted'])

    def test_other_participant_cannot_edit_or_delete_message(self):
        message = self.create_message(content='Alice owns this')
        self.client.force_authenticate(self.bob)

        edit_response = self.client.patch(
            reverse('message-detail', kwargs={'pk': message.id}),
            {'content': 'Hijacked'},
            format='json',
        )
        delete_response = self.client.delete(reverse('message-detail', kwargs={'pk': message.id}))

        self.assertEqual(edit_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(delete_response.status_code, status.HTTP_403_FORBIDDEN)
        message.refresh_from_db()
        self.assertEqual(message.content, 'Alice owns this')
        self.assertIsNone(message.deleted_at)

    def test_loading_and_opening_conversation_updates_delivery_and_read_receipts(self):
        message = self.create_message(sender=self.alice, content='Track me')
        receipt = MessageReceipt.objects.get(message=message, user=self.bob)
        self.assertIsNone(receipt.delivered_at)
        self.assertIsNone(receipt.read_at)

        self.client.force_authenticate(self.bob)
        load_response = self.client.get(reverse('conversation-messages', kwargs={'pk': self.conversation.id}))
        self.assertEqual(load_response.status_code, status.HTTP_200_OK)
        receipt.refresh_from_db()
        self.assertIsNotNone(receipt.delivered_at)
        self.assertIsNone(receipt.read_at)

        read_response = self.client.post(reverse('conversation-mark-read', kwargs={'pk': self.conversation.id}))
        self.assertEqual(read_response.status_code, status.HTTP_200_OK)
        self.assertEqual(read_response.data['updated_count'], 1)
        receipt.refresh_from_db()
        message.refresh_from_db()
        self.assertIsNotNone(receipt.read_at)
        self.assertTrue(message.is_read)


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

    def test_websocket_sends_reply_and_creates_notification(self):
        async_to_sync(self._websocket_sends_reply_and_creates_notification)()

    async def _websocket_sends_reply_and_creates_notification(self):
        original_id = await self._create_original_message()
        token = str(AccessToken.for_user(self.alice))
        communicator = WebsocketCommunicator(
            application,
            f'/ws/conversations/{self.conversation.id}/?token={token}',
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        await communicator.send_json_to({'content': 'Realtime reply', 'reply_to': original_id})
        response = await communicator.receive_json_from()

        self.assertEqual(response['type'], 'message.created')
        self.assertEqual(response['message']['content'], 'Realtime reply')
        self.assertEqual(response['message']['reply_to'], original_id)
        self.assertEqual(response['message']['status'], 'sent')

        await communicator.disconnect()

        self.assertEqual(await self._message_count(), 1)
        self.assertEqual(await self._notification_count(), 1)

    @database_sync_to_async
    def _create_original_message(self):
        message = Message.objects.create(conversation=self.conversation, sender=self.bob, content='Original')
        ensure_message_receipts(message)
        return message.id

    @database_sync_to_async
    def _message_count(self):
        return Message.objects.filter(conversation=self.conversation, sender=self.alice, content='Realtime reply').count()

    @database_sync_to_async
    def _notification_count(self):
        return Notification.objects.filter(recipient=self.bob, actor=self.alice, verb=Notification.Verb.MESSAGE).count()
