from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Advertisement, Report, SavedAdvertisement

User = get_user_model()


class MarketplaceApiTests(APITestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            email='seller@flow.test', university_id='SELL001', password='pass12345',
            user_name='seller', is_active=True,
        )
        self.buyer = User.objects.create_user(
            email='buyer@flow.test', university_id='BUY001', password='pass12345',
            user_name='buyer', is_active=True,
        )
        self.other = User.objects.create_user(
            email='other@flow.test', university_id='OTHM001', password='pass12345',
            user_name='other', is_active=True,
        )
        self.listing = Advertisement.objects.create(
            user=self.seller,
            title='Clean engineering calculator',
            description='A reliable scientific calculator in excellent condition.',
            price=Decimal('12500.00'),
            category=Advertisement.Category.ELECTRONICS,
            condition=Advertisement.Condition.LIKE_NEW,
            location='Faculty of Science',
        )
        self.client.force_authenticate(self.buyer)

    def test_listings_are_searchable_and_return_structured_seller(self):
        response = self.client.get(
            reverse('marketplace-listing-list'),
            {'q': 'calculator', 'category': Advertisement.Category.ELECTRONICS},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.data['results'] if isinstance(response.data, dict) and 'results' in response.data else response.data
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]['seller']['id'], self.seller.id)
        self.assertEqual(payload[0]['currency'], 'NGN')

    def test_authenticated_seller_can_create_and_manage_listing(self):
        self.client.force_authenticate(self.seller)
        response = self.client.post(
            reverse('marketplace-listing-list'),
            {
                'title': 'CSC 302 textbook',
                'description': 'Original course textbook with clean pages and no missing chapters.',
                'price': '8500.00',
                'category': Advertisement.Category.BOOKS,
                'condition': Advertisement.Condition.USED,
                'location': 'Computer Science department',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        listing_id = response.data['id']

        status_response = self.client.post(
            reverse('marketplace-listing-set-status', kwargs={'pk': listing_id}),
            {'status': Advertisement.Status.SOLD},
            format='json',
        )
        self.assertEqual(status_response.status_code, status.HTTP_200_OK)
        self.assertEqual(status_response.data['status'], Advertisement.Status.SOLD)

        delete_response = self.client.delete(reverse('marketplace-listing-detail', kwargs={'pk': listing_id}))
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Advertisement.objects.get(id=listing_id).status, Advertisement.Status.ARCHIVED)

    def test_non_owner_cannot_update_or_archive_listing(self):
        response = self.client.patch(
            reverse('marketplace-listing-detail', kwargs={'pk': self.listing.id}),
            {'title': 'Hijacked title'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.delete(reverse('marketplace-listing-detail', kwargs={'pk': self.listing.id}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_saved_listings_are_private_to_each_user(self):
        save_response = self.client.post(reverse('marketplace-listing-save-listing', kwargs={'pk': self.listing.id}))
        self.assertEqual(save_response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(SavedAdvertisement.objects.filter(user=self.buyer, advertisement=self.listing).exists())

        saved_response = self.client.get(reverse('marketplace-listing-saved'))
        saved_payload = saved_response.data['results'] if isinstance(saved_response.data, dict) and 'results' in saved_response.data else saved_response.data
        self.assertEqual([item['id'] for item in saved_payload], [self.listing.id])

        self.client.force_authenticate(self.other)
        other_response = self.client.get(reverse('marketplace-listing-saved'))
        other_payload = other_response.data['results'] if isinstance(other_response.data, dict) and 'results' in other_response.data else other_response.data
        self.assertEqual(other_payload, [])

    def test_reporting_is_idempotent_per_user(self):
        url = reverse('marketplace-listing-report', kwargs={'pk': self.listing.id})
        first = self.client.post(url, {'reason': 'The listing appears to use misleading product information.'}, format='json')
        second = self.client.post(url, {'reason': 'The price and description appear deliberately misleading.'}, format='json')

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(Report.objects.filter(reporter=self.buyer, advertisement=self.listing).count(), 1)

    def test_retrieve_increments_views_only_for_non_owner(self):
        self.client.get(reverse('marketplace-listing-detail', kwargs={'pk': self.listing.id}))
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.views_count, 1)

        self.client.force_authenticate(self.seller)
        self.client.get(reverse('marketplace-listing-detail', kwargs={'pk': self.listing.id}))
        self.listing.refresh_from_db()
        self.assertEqual(self.listing.views_count, 1)
