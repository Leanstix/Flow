from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from messaging.models import MessageAttachment

from .models import Advertisement

User = get_user_model()


class MarketplaceContactContextTests(APITestCase):
    def setUp(self):
        self.seller = User.objects.create_user(
            email='seller-context@example.com', university_id='SELL001',
            password='pass12345', user_name='sellercontext', is_active=True,
        )
        self.buyer = User.objects.create_user(
            email='buyer-context@example.com', university_id='BUY001',
            password='pass12345', user_name='buyercontext', is_active=True,
        )
        self.listing = Advertisement.objects.create(
            user=self.seller,
            title='Calculus textbook',
            description='Clean copy with all chapters intact.',
            price='4500.00',
            category=Advertisement.Category.BOOKS,
            condition=Advertisement.Condition.USED,
        )
        self.client.force_authenticate(self.buyer)

    def test_contact_seller_message_contains_clickable_listing_card(self):
        response = self.client.post(
            reverse('marketplace-listing-contact-seller', kwargs={'pk': self.listing.id}),
            {'message': 'Is this still available?'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['message']['content'], 'Is this still available?')
        attachment = response.data['message']['attachments'][0]
        self.assertEqual(attachment['kind'], MessageAttachment.Kind.LISTING)
        self.assertEqual(attachment['metadata']['listing_id'], self.listing.id)
        self.assertEqual(attachment['metadata']['route'], f'/marketplace/{self.listing.id}')
        self.assertEqual(
            set(response.data['conversation']['participants'][index]['id'] for index in range(2)),
            {self.seller.id, self.buyer.id},
        )

    def test_seller_cannot_contact_self(self):
        self.client.force_authenticate(self.seller)
        response = self.client.post(
            reverse('marketplace-listing-contact-seller', kwargs={'pk': self.listing.id}),
            {},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
