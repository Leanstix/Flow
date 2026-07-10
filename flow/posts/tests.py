from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from notifications.models import Notification

from .models import Comment, Like, Post

User = get_user_model()


class PostInteractionTests(APITestCase):
    def setUp(self):
        self.author = User.objects.create_user(
            email='author@example.com',
            university_id='AUTH001',
            password='pass12345',
            user_name='author',
            is_active=True,
        )
        self.viewer = User.objects.create_user(
            email='viewer@example.com',
            university_id='VIEW001',
            password='pass12345',
            user_name='viewer',
            is_active=True,
        )
        self.client.force_authenticate(self.viewer)
        self.post = Post.objects.create(user=self.author, content='Original campus update')

    def test_toggle_like_creates_and_removes_like_with_notification(self):
        response = self.client.post(reverse('toggle_like', kwargs={'post_id': self.post.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['liked'])
        self.assertEqual(Like.objects.filter(user=self.viewer, post=self.post).count(), 1)
        self.assertEqual(
            Notification.objects.filter(recipient=self.author, actor=self.viewer, verb=Notification.Verb.LIKE).count(),
            1,
        )

        response = self.client.post(reverse('toggle_like', kwargs={'post_id': self.post.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['liked'])
        self.assertFalse(Like.objects.filter(user=self.viewer, post=self.post).exists())

    def test_add_comment_and_reply_to_comment(self):
        comment_response = self.client.post(
            reverse('add_comment', kwargs={'post_id': self.post.id}),
            {'content': 'This is helpful'},
            format='json',
        )

        self.assertEqual(comment_response.status_code, status.HTTP_201_CREATED)
        comment = Comment.objects.get(id=comment_response.data['id'])
        self.assertIsNone(comment.parent)
        self.assertEqual(comment.post, self.post)
        self.assertEqual(
            Notification.objects.filter(recipient=self.author, actor=self.viewer, verb=Notification.Verb.COMMENT).count(),
            1,
        )

        self.client.force_authenticate(self.author)
        reply_response = self.client.post(
            reverse('reply_to_comment', kwargs={'comment_id': comment.id}),
            {'content': 'Glad it helped'},
            format='json',
        )

        self.assertEqual(reply_response.status_code, status.HTTP_201_CREATED)
        reply = Comment.objects.get(id=reply_response.data['id'])
        self.assertEqual(reply.parent, comment)
        self.assertEqual(reply.post, self.post)
        self.assertEqual(comment.replies_count, 1)
        self.assertEqual(
            Notification.objects.filter(recipient=self.viewer, actor=self.author, verb=Notification.Verb.COMMENT_REPLY).count(),
            1,
        )

    def test_repost_keeps_original_reference_and_notifies_author(self):
        response = self.client.post(
            reverse('repost', kwargs={'post_id': self.post.id}),
            {'content': 'Sharing this'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        repost = Post.objects.get(id=response.data['id'])
        self.assertEqual(repost.reposted_from, self.post)
        self.assertEqual(repost.content, 'Sharing this')
        self.assertEqual(self.post.reposts_count, 1)
        self.assertEqual(
            Notification.objects.filter(recipient=self.author, actor=self.viewer, verb=Notification.Verb.REPOST).count(),
            1,
        )

    def test_search_uses_user_name_not_missing_username_field(self):
        response = self.client.get(reverse('search_posts'), {'q': 'author'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_ids = [item['id'] for item in response.data['results']]
        self.assertIn(self.post.id, result_ids)

    def test_all_feed_orders_by_engagement_descending(self):
        quiet_post = Post.objects.create(user=self.author, content='Quiet update')
        Like.objects.create(user=self.viewer, post=self.post)
        Comment.objects.create(user=self.viewer, post=self.post, content='Engaging comment')

        response = self.client.get(reverse('all_feed'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        result_ids = [item['id'] for item in response.data['results']]
        self.assertLess(result_ids.index(self.post.id), result_ids.index(quiet_post.id))
