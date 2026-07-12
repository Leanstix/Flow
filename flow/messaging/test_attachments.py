from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Conversation, Message, MessageAttachment

User = get_user_model()


def image_upload():
    output = BytesIO()
    Image.new('RGB', (10, 10), 'blue').save(output, format='PNG')
    return SimpleUploadedFile('message.png', output.getvalue(), content_type='image/png')


class MessageAttachmentTests(APITestCase):
    def setUp(self):
        self.alice = User.objects.create_user(
            email='attach-alice@example.com', university_id='ATT001',
            password='pass12345', user_name='attachalice', is_active=True,
        )
        self.bob = User.objects.create_user(
            email='attach-bob@example.com', university_id='ATT002',
            password='pass12345', user_name='attachbob', is_active=True,
        )
        self.conversation = Conversation.objects.create()
        self.conversation.participants.set([self.alice, self.bob])
        self.client.force_authenticate(self.alice)

    def test_photo_can_be_sent_without_text_when_type_is_explicit(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            response = self.client.post(
                reverse('conversation-send-message', kwargs={'pk': self.conversation.id}),
                {
                    'content': '',
                    'attachment_type': MessageAttachment.Kind.IMAGE,
                    'files': [image_upload()],
                },
                format='multipart',
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], '')
        self.assertEqual(response.data['attachments'][0]['kind'], 'image')
        self.assertTrue(response.data['attachments'][0]['url'])

    def test_file_upload_requires_an_attachment_category(self):
        response = self.client.post(
            reverse('conversation-send-message', kwargs={'pk': self.conversation.id}),
            {'files': [image_upload()]},
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('attachment_type', response.data)

    def test_structured_location_attachment_is_supported(self):
        response = self.client.post(
            reverse('conversation-send-message', kwargs={'pk': self.conversation.id}),
            {
                'attachment_type': MessageAttachment.Kind.LOCATION,
                'attachment_payload': {'latitude': 7.3775, 'longitude': 3.9470, 'label': 'University of Ibadan'},
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        attachment = Message.objects.get(pk=response.data['id']).attachments.get()
        self.assertEqual(attachment.kind, MessageAttachment.Kind.LOCATION)
        self.assertEqual(attachment.metadata['label'], 'University of Ibadan')
