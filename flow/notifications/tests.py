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

from .models import Notification
from .services import create_notification

User = get_user_model()

TEST_CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}


class NotificationApiTests(APITestCase):
    def setUp(self):
        self.actor = User.objects.create_user(
            email='actor@example.com', university_id='ACT001', password='pass12345',
            user_name='actor', is_active=True,
        )
        self.recipient = User.objects.create_user(
            email='recipient@example.com', university_id='REC001', password='pass12345',
            user_name='recipient', is_active=True,
        )
        self.other = User.objects.create_user(
            email='other@example.com', university_id='OTH001', password='pass12345',
            user_name='other', is_active=True,
        )
        self.client.force_authenticate(self.recipient)

    def test_list_only_returns_authenticated_users_notifications(self):
        own_notification = create_notification(
            recipient=self.recipient, actor=self.actor,
            verb=Notification.Verb.SYSTEM, message='Owned notification',
        )
        create_notification(
            recipient=self.other, actor=self.actor,
            verb=Notification.Verb.SYSTEM, message='Other notification',
        )

        response = self.client.get(reverse('notification-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data['results'] if isinstance(response.data, dict) and 'results' in response.data else response.data
        ids = [item['id'] for item in payload]
        self.assertEqual(ids, [own_notification.id])

    def test_user_cannot_retrieve_or_mark_another_users_notification(self):
        other_notification = create_notification(
            recipient=self.other, actor=self.actor,
            verb=Notification.Verb.SYSTEM, message='Private to other user',
        )

        detail = self.client.get(reverse('notification-detail', kwargs={'pk': other_notification.id}))
        mark_read = self.client.post(reverse('notification-mark-read', kwargs={'pk': other_notification.id}))

        self.assertEqual(detail.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(mark_read.status_code, status.HTTP_404_NOT_FOUND)
        other_notification.refresh_from_db()
        self.assertFalse(other_notification.is_read)

    def test_unread_count_and_mark_read(self):
        notification = create_notification(
            recipient=self.recipient, actor=self.actor,
            verb=Notification.Verb.SYSTEM, message='Unread notification',
        )
        create_notification(
            recipient=self.other, actor=self.actor,
            verb=Notification.Verb.SYSTEM, message='Someone else unread',
        )

        count_response = self.client.get(reverse('notification-unread-count'))
        self.assertEqual(count_response.status_code, status.HTTP_200_OK)
        self.assertEqual(count_response.data['unread_count'], 1)

        mark_response = self.client.post(reverse('notification-mark-read', kwargs={'pk': notification.id}))
        self.assertEqual(mark_response.status_code, status.HTTP_200_OK)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_mark_all_read_only_updates_current_user(self):
        create_notification(recipient=self.recipient, actor=self.actor, verb=Notification.Verb.SYSTEM, message='One')
        create_notification(recipient=self.recipient, actor=self.actor, verb=Notification.Verb.SYSTEM, message='Two')
        other_notification = create_notification(recipient=self.other, actor=self.actor, verb=Notification.Verb.SYSTEM, message='Other')

        response = self.client.post(reverse('notification-mark-all-read'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['updated_count'], 2)
        self.assertEqual(Notification.objects.filter(recipient=self.recipient, is_read=False).count(), 0)
        other_notification.refresh_from_db()
        self.assertFalse(other_notification.is_read)


@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS, ALLOWED_HOSTS=['testserver', 'localhost'])
class NotificationWebsocketIsolationTests(TransactionTestCase):
    def setUp(self):
        self.actor = User.objects.create_user(
            email='ws-actor@example.com', university_id='WSACT001', password='pass12345',
            user_name='wsactor', is_active=True,
        )
        self.alice = User.objects.create_user(
            email='ws-alice@example.com', university_id='WSAL001', password='pass12345',
            user_name='wsalice', is_active=True,
        )
        self.bob = User.objects.create_user(
            email='ws-bob@example.com', university_id='WSBOB001', password='pass12345',
            user_name='wsbob', is_active=True,
        )

    def test_notification_is_delivered_only_to_its_recipient_socket(self):
        async_to_sync(self._notification_is_delivered_only_to_its_recipient_socket)()

    async def _notification_is_delivered_only_to_its_recipient_socket(self):
        alice = WebsocketCommunicator(application, f'/ws/notifications/?token={AccessToken.for_user(self.alice)}')
        bob = WebsocketCommunicator(application, f'/ws/notifications/?token={AccessToken.for_user(self.bob)}')
        alice_connected, _ = await alice.connect()
        bob_connected, _ = await bob.connect()
        self.assertTrue(alice_connected)
        self.assertTrue(bob_connected)

        notification_id = await self._create_for_alice()
        payload = await alice.receive_json_from(timeout=1)

        self.assertEqual(payload['type'], 'notification.created')
        self.assertEqual(payload['notification']['id'], notification_id)
        self.assertEqual(payload['notification']['recipient'], self.alice.id)
        self.assertTrue(await bob.receive_nothing(timeout=0.1))

        await alice.disconnect()
        await bob.disconnect()

    @database_sync_to_async
    def _create_for_alice(self):
        notification = create_notification(
            recipient=self.alice,
            actor=self.actor,
            verb=Notification.Verb.SYSTEM,
            message='Only Alice should receive this.',
        )
        return notification.id
