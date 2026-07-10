import json
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, SimpleTestCase, TestCase, override_settings

from .cloudinary_utils import upload_profile_picture
from .models import Interest
from .serializers import UserRegistrationSerializer
from .views import UserProfileUpdateView

User = get_user_model()


class UserManagerTests(TestCase):
    def test_create_user_hashes_password_and_normalizes_email(self):
        user = User.objects.create_user(
            email='Student@Example.COM',
            university_id='UNI001',
            password='pass12345',
            user_name='student',
        )

        self.assertEqual(user.email, 'Student@example.com')
        self.assertTrue(user.check_password('pass12345'))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_superuser_sets_required_flags(self):
        admin = User.objects.create_superuser(
            email='admin@example.com',
            university_id='ADM001',
            password='pass12345',
            user_name='admin',
        )

        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_user_interests_relation_matches_profile_serializer_expectation(self):
        user = User.objects.create_user(
            email='interest@example.com',
            university_id='INT001',
            password='pass12345',
            user_name='interest_user',
        )
        interest = Interest.objects.create(name='Software Engineering')

        user.interests.add(interest)

        self.assertEqual(list(user.interests.all()), [interest])


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='Flow <no-reply@flow.test>',
    FRONTEND_URL='http://localhost:3000',
)
class RegistrationEmailTests(TestCase):
    def test_registration_sends_activation_link(self):
        serializer = UserRegistrationSerializer(
            data={
                'email': 'new-user@example.com',
                'university_id': 'NEW001',
                'password': 'SecurePass!4829',
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        expected_url = f'http://localhost:3000/activate?token={user.activation_token}'
        self.assertEqual(message.to, [user.email])
        self.assertIn(expected_url, message.body)
        self.assertIn(expected_url, message.alternatives[0][0])

    @patch(
        'userauth.emails.EmailMultiAlternatives.send',
        side_effect=RuntimeError('SMTP unavailable'),
    )
    def test_failed_delivery_rolls_back_registration(self, send):
        client = Client()

        response = client.post(
            '/api/userauth/register/',
            data=json.dumps(
                {
                    'email': 'delivery-failed@example.com',
                    'university_id': 'FAIL001',
                    'password': 'SecurePass!4829',
                }
            ),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 503)
        self.assertFalse(User.objects.filter(email='delivery-failed@example.com').exists())
        send.assert_called_once()


class CloudinaryUploadTests(TestCase):
    @override_settings(
        CLOUDINARY_URL='cloudinary://api-key:api-secret@demo-cloud',
        CLOUDINARY_PROFILE_FOLDER='flow/profile_pictures',
    )
    @patch('userauth.cloudinary_utils.cloudinary.uploader.upload')
    def test_upload_profile_picture_returns_secure_url(self, upload):
        upload.return_value = {
            'secure_url': 'https://res.cloudinary.com/demo-cloud/image/upload/avatar.png'
        }
        image = SimpleUploadedFile('avatar.png', b'image-data', content_type='image/png')

        result = upload_profile_picture(image)

        self.assertEqual(result, upload.return_value['secure_url'])
        upload.assert_called_once_with(
            image,
            folder='flow/profile_pictures',
            resource_type='image',
            use_filename=True,
            unique_filename=True,
            overwrite=False,
        )

    @override_settings(
        CLOUDINARY_URL=None,
        CLOUDINARY_CLOUD_NAME=None,
        CLOUDINARY_API_KEY=None,
        CLOUDINARY_API_SECRET=None,
    )
    @patch('userauth.cloudinary_utils.cloudinary.uploader.upload')
    def test_upload_requires_cloudinary_credentials(self, upload):
        image = SimpleUploadedFile('avatar.png', b'image-data', content_type='image/png')

        with self.assertRaisesMessage(ValueError, 'Cloudinary is not configured'):
            upload_profile_picture(image)

        upload.assert_not_called()


class UserProfileUpdateTests(SimpleTestCase):
    @patch('userauth.views.upload_profile_picture')
    def test_profile_picture_is_uploaded_to_cloudinary(self, upload):
        cloudinary_url = (
            'https://res.cloudinary.com/demo-cloud/image/upload/flow/profile_pictures/avatar.png'
        )
        upload.return_value = cloudinary_url
        image = SimpleUploadedFile('avatar.png', b'image-data', content_type='image/png')
        request = Mock(
            data={'first_name': 'Ada', 'profile_picture': image},
            FILES={'profile_picture': image},
        )
        user = Mock(email='profile@example.com')
        serializer = Mock(data={'first_name': 'Ada', 'profile_picture': cloudinary_url})
        serializer.is_valid.return_value = True
        view = UserProfileUpdateView()
        view.get_object = Mock(return_value=user)
        view.get_serializer = Mock(return_value=serializer)
        view.perform_update = Mock()

        response = view.update(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['profile_picture'], cloudinary_url)
        upload.assert_called_once_with(image)
        view.get_serializer.assert_called_once_with(
            user,
            data={'first_name': 'Ada', 'profile_picture': cloudinary_url},
            partial=True,
        )
        view.perform_update.assert_called_once_with(serializer)
