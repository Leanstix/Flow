from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from notifications.models import Notification

from .models import Community, CommunityMembership, CommunityPost, CommunityResource

User = get_user_model()


class CommunityApiTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='owner@flow.test', university_id='OWNER001', password='pass12345',
            user_name='owner', is_active=True,
        )
        self.member = User.objects.create_user(
            email='member@flow.test', university_id='MEMBER001', password='pass12345',
            user_name='member', is_active=True,
        )
        self.outsider = User.objects.create_user(
            email='outsider@flow.test', university_id='OUT001', password='pass12345',
            user_name='outsider', is_active=True,
        )
        self.client.force_authenticate(self.owner)

    def create_community(self, visibility=Community.Visibility.PUBLIC):
        response = self.client.post(
            reverse('community-list'),
            {
                'name': 'CSC 301 Study Circle' if visibility == Community.Visibility.PUBLIC else 'Private Builders',
                'description': 'A focused student community for coursework and projects.',
                'category': Community.Category.COURSE if visibility == Community.Visibility.PUBLIC else Community.Category.PROJECT,
                'visibility': visibility,
                'course_code': 'CSC 301' if visibility == Community.Visibility.PUBLIC else '',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return Community.objects.get(id=response.data['id'])

    def test_create_group_creates_owner_membership(self):
        community = self.create_community()

        membership = CommunityMembership.objects.get(community=community, user=self.owner)
        self.assertEqual(membership.role, CommunityMembership.Role.OWNER)
        self.assertEqual(membership.status, CommunityMembership.Status.ACTIVE)

    def test_public_group_join_is_immediate(self):
        community = self.create_community()
        self.client.force_authenticate(self.member)

        response = self.client.post(reverse('community-join', kwargs={'slug': community.slug}))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        membership = CommunityMembership.objects.get(community=community, user=self.member)
        self.assertEqual(membership.status, CommunityMembership.Status.ACTIVE)

    def test_private_group_requires_owner_approval_and_only_notifies_owner(self):
        community = self.create_community(Community.Visibility.PRIVATE)
        self.client.force_authenticate(self.member)

        join_response = self.client.post(reverse('community-join', kwargs={'slug': community.slug}))

        self.assertEqual(join_response.status_code, status.HTTP_201_CREATED)
        membership = CommunityMembership.objects.get(community=community, user=self.member)
        self.assertEqual(membership.status, CommunityMembership.Status.PENDING)
        self.assertEqual(Notification.objects.filter(recipient=self.owner).count(), 1)
        self.assertEqual(Notification.objects.filter(recipient=self.outsider).count(), 0)

        self.client.force_authenticate(self.owner)
        approve_response = self.client.post(
            reverse('community-approve-member', kwargs={'slug': community.slug, 'membership_id': membership.id})
        )

        self.assertEqual(approve_response.status_code, status.HTTP_200_OK)
        membership.refresh_from_db()
        self.assertEqual(membership.status, CommunityMembership.Status.ACTIVE)
        self.assertEqual(Notification.objects.filter(recipient=self.member).count(), 1)
        self.assertEqual(Notification.objects.filter(recipient=self.outsider).count(), 0)

    def test_only_active_members_can_post(self):
        community = self.create_community()
        self.client.force_authenticate(self.outsider)

        denied = self.client.post(
            reverse('community-post-list'),
            {'community': community.id, 'content': 'I should not be able to post.'},
            format='json',
        )
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(self.member)
        self.client.post(reverse('community-join', kwargs={'slug': community.slug}))
        allowed = self.client.post(
            reverse('community-post-list'),
            {'community': community.id, 'content': 'Here are my lecture notes.'},
            format='json',
        )
        self.assertEqual(allowed.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CommunityPost.objects.filter(community=community, author=self.member).count(), 1)

    def test_private_resources_are_visible_only_to_active_members(self):
        community = self.create_community(Community.Visibility.PRIVATE)
        CommunityResource.objects.create(
            community=community,
            uploaded_by=self.owner,
            title='Project brief',
            url='https://example.com/project-brief.pdf',
        )

        self.client.force_authenticate(self.outsider)
        response = self.client.get(reverse('community-resource-list'), {'community': community.slug})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data['results'] if isinstance(response.data, dict) and 'results' in response.data else response.data
        self.assertEqual(payload, [])

        self.client.force_authenticate(self.owner)
        response = self.client.get(reverse('community-resource-list'), {'community': community.slug})
        payload = response.data['results'] if isinstance(response.data, dict) and 'results' in response.data else response.data
        self.assertEqual(len(payload), 1)
