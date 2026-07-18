import json
from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from notifications.models import Notification
from requests.models import FriendRequest

from .models import Comment, Hashtag, Post, PostMedia

User = get_user_model()


def tiny_png():
    output = BytesIO()
    Image.new('RGB', (8, 8), 'white').save(output, format='PNG')
    return SimpleUploadedFile('campus.png', output.getvalue(), content_type='image/png')


class SocialFeatureTests(APITestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            email='social-author@example.com', university_id='SOC001',
            password='pass12345', user_name='author', is_active=True,
        )
        self.mentioned = User.objects.create_user(
            email='mentioned@example.com', university_id='SOC002',
            password='pass12345', user_name='mentioned_user', is_active=True,
        )
        self.client.force_authenticate(self.author)

    def test_post_indexes_hashtags_and_notifies_explicit_mentions(self):
        response = self.client.post(
            reverse('posts'),
            {
                'content': 'Building for #CampusTech with @mentioned_user',
                'mention_user_ids': [self.mentioned.id],
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        post = Post.objects.get(pk=response.data['id'])
        self.assertTrue(post.hashtags.filter(name='campustech').exists())
        self.assertTrue(post.mentioned_users.filter(pk=self.mentioned.pk).exists())
        self.assertEqual(response.data['mentions'][0]['id'], self.mentioned.id)
        self.assertTrue(Notification.objects.filter(
            recipient=self.mentioned,
            actor=self.author,
            verb=Notification.Verb.MENTION,
            target_post=post,
        ).exists())

        search = self.client.get(reverse('hashtag_posts', kwargs={'tag': 'campustech'}))
        self.assertEqual(search.status_code, status.HTTP_200_OK)
        self.assertEqual(search.data['results'][0]['id'], post.id)

    def test_multipart_post_decodes_json_mention_ids(self):
        response = self.client.post(
            reverse('posts'),
            {
                'content': 'Building with @mentioned_user',
                'mention_user_ids': json.dumps([self.mentioned.id]),
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['mentions'][0]['id'], self.mentioned.id)

    def test_multipart_post_accepts_empty_json_mention_ids(self):
        response = self.client.post(
            reverse('posts'),
            {
                'content': 'A post without mentions',
                'mention_user_ids': json.dumps([]),
            },
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['mentions'], [])

    def test_unselected_at_text_remains_plain_text(self):
        response = self.client.post(
            reverse('posts'),
            {'content': 'This is plain text: @mentioned_user'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        post = Post.objects.get(pk=response.data['id'])
        self.assertFalse(post.mentioned_users.exists())
        self.assertEqual(response.data['mentions'], [])
        self.assertFalse(Notification.objects.filter(
            recipient=self.mentioned,
            verb=Notification.Verb.MENTION,
            target_post=post,
        ).exists())

    def test_selected_mention_must_exist_in_content(self):
        response = self.client.post(
            reverse('posts'),
            {
                'content': 'No mention token here',
                'mention_user_ids': [self.mentioned.id],
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('mention_user_ids', response.data)
        self.assertFalse(Post.objects.filter(content='No mention token here').exists())

    def test_mention_suggestions_use_friends_then_global_active_users(self):
        FriendRequest.objects.create(from_user=self.author, to_user=self.mentioned, accepted=True)
        global_user = User.objects.create_user(
            email='global@example.com', university_id='SOC003',
            password='pass12345', user_name='global_match', is_active=True,
        )
        User.objects.create_user(
            email='inactive@example.com', university_id='SOC004',
            password='pass12345', user_name='inactive_match', is_active=False,
        )

        friends_response = self.client.get(reverse('search-users'), {'context': 'mention', 'q': ''})
        self.assertEqual(friends_response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['id'] for item in friends_response.data], [self.mentioned.id])
        self.assertTrue(friends_response.data[0]['is_friends'])

        global_response = self.client.get(reverse('search-users'), {'context': 'mention', 'q': 'global'})
        self.assertEqual(global_response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['id'] for item in global_response.data], [global_user.id])
        self.assertFalse(global_response.data[0]['is_friends'])

        inactive_response = self.client.get(reverse('search-users'), {'context': 'mention', 'q': 'inactive'})
        self.assertEqual(inactive_response.status_code, status.HTTP_200_OK)
        self.assertEqual(inactive_response.data, [])

    def test_replies_can_continue_without_a_depth_limit(self):
        post = Post.objects.create(user=self.author, content='Thread')
        root = Comment.objects.create(user=self.author, post=post, content='Root')
        first = Comment.objects.create(user=self.mentioned, post=post, parent=root, content='First')
        second = Comment.objects.create(user=self.author, post=post, parent=first, content='Second')
        third = Comment.objects.create(user=self.mentioned, post=post, parent=second, content='Third')

        self.assertEqual((root.depth, first.depth, second.depth, third.depth), (0, 1, 2, 3))
        self.assertEqual(first.root_id, root.id)
        response = self.client.get(reverse('get_comment_replies', kwargs={'comment_id': root.id}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['depth'] for item in response.data['results']], [1, 2, 3])

    def test_image_post_is_stored_as_normalized_media(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            response = self.client.post(
                reverse('posts'),
                {'content': 'Photo update', 'platform': 'mobile', 'media': [tiny_png()]},
                format='multipart',
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        media = PostMedia.objects.get(post_id=response.data['id'])
        self.assertEqual(media.media_type, PostMedia.MediaType.IMAGE)
        self.assertTrue(media.url)

    def test_web_video_limit_is_ninety_seconds(self):
        video = SimpleUploadedFile('long.mp4', b'not-read-because-validation-runs-first', content_type='video/mp4')
        response = self.client.post(
            reverse('posts'),
            {
                'content': 'Too long for web',
                'platform': 'web',
                'media': [video],
                'media_metadata': json.dumps([{'duration_seconds': 91}]),
            },
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('media', response.data)

    def test_mobile_rejects_server_side_trim_offsets(self):
        source_video = SimpleUploadedFile(
            'untrimmed-source.mp4',
            b'validation-rejects-before-media-processing',
            content_type='video/mp4',
        )
        response = self.client.post(
            reverse('posts'),
            {
                'content': 'This source should never reach media processing',
                'platform': 'mobile',
                'media': [source_video],
                'media_metadata': json.dumps([{
                    'duration_seconds': 300,
                    'trim_start_seconds': 30,
                    'trim_end_seconds': 150,
                }]),
            },
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('media_metadata', response.data)
        self.assertIn('export the final video on the device', str(response.data['media_metadata']))
        self.assertFalse(Post.objects.filter(content__icontains='source should never').exists())

    def test_mobile_accepts_final_export_duration_without_trim_offsets(self):
        final_video = SimpleUploadedFile(
            'final-export.mp4',
            b'final-client-export',
            content_type='video/mp4',
        )
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            response = self.client.post(
                reverse('posts'),
                {
                    'content': 'Final exported video',
                    'platform': 'mobile',
                    'media': [final_video],
                    'media_metadata': json.dumps([{'duration_seconds': 120}]),
                },
                format='multipart',
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        media = PostMedia.objects.get(post_id=response.data['id'])
        self.assertEqual(float(media.duration_seconds), 120.0)
        self.assertEqual(float(media.trim_start_seconds), 0.0)
        self.assertIsNone(media.trim_end_seconds)

    def test_hashtag_suggestions_are_ranked(self):
        popular = Hashtag.objects.create(name='popular')
        post = Post.objects.create(user=self.author, content='#popular')
        post.hashtags.add(popular)
        response = self.client.get(reverse('hashtag_search'), {'q': 'pop'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['name'], 'popular')
