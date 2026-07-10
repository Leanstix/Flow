from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Interest

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
