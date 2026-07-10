from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Notification
from .services import create_notification

User = get_user_model()


class NotificationApiTests(APITestCase):
    def setUp(self):
        self.actor = User.objects.create_user(
            email='actor@example.com',
            university_id='ACT001',
            password='pass12345',
            user_name='actor',
            is_active=True,
        )
        self.recipient = User.objects.create_user(
            email='recipient@example.com',
            university_id='REC001',
            password='pass12345',
            user_name='recipient',
            is_active=True,
        )
        self.other = User.objects.create_user(
            email='other@example.com',
            university_id='OTH001',
            password='pass12345',
            user_name='other',
            is_active=True,
        )
        self.client.force_authenticate(self.recipient)

    def test_list_only_returns_authenticated_users_notifications(self):
        own_notification = create_notification(
            recipient=self.recipient,
            actor=self.actor,
            verb=Notification.Verb.SYSTEM,
            message='Owned notification',
        )
        create_notification(
            recipient=self.other,
            actor=self.actor,
            verb=Notification.Verb.SYSTEM,
            message='Other notification',
        )

        response = self.client.get(reverse('notification-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data['results'] if isinstance(response.data, dict) and 'results' in response.data else response.data
        ids = [item['id'] for item in payload]
        self.assertEqual(ids, [own_notification.id])

    def test_unread_count_and_mark_read(self):
        notification = create_notification(
            recipient=self.recipient,
            actor=self.actor,
            verb=Notification.Verb.SYSTEM,
            message='Unread notification',
        )

        count_response = self.client.get(reverse('notification-unread-count'))
        self.assertEqual(count_response.status_code, status.HTTP_200_OK)
        self.assertEqual(count_response.data['unread_count'], 1)

        mark_response = self.client.post(reverse('notification-mark-read', kwargs={'pk': notification.id}))
        self.assertEqual(mark_response.status_code, status.HTTP_200_OK)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_mark_all_read(self):
        create_notification(recipient=self.recipient, actor=self.actor, verb=Notification.Verb.SYSTEM, message='One')
        create_notification(recipient=self.recipient, actor=self.actor, verb=Notification.Verb.SYSTEM, message='Two')

        response = self.client.post(reverse('notification-mark-all-read'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['updated_count'], 2)
        self.assertEqual(Notification.objects.filter(recipient=self.recipient, is_read=False).count(), 0)
