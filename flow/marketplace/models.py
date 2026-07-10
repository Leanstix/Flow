import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Advertisement(models.Model):
    class Category(models.TextChoices):
        BOOKS = 'books', 'Books and study materials'
        ELECTRONICS = 'electronics', 'Electronics'
        FASHION = 'fashion', 'Fashion'
        SERVICES = 'services', 'Services'
        ACCOMMODATION = 'accommodation', 'Accommodation'
        FOOD = 'food', 'Food'
        OTHER = 'other', 'Other'

    class Condition(models.TextChoices):
        NEW = 'new', 'New'
        LIKE_NEW = 'like_new', 'Like new'
        USED = 'used', 'Used'
        NOT_APPLICABLE = 'not_applicable', 'Not applicable'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        RESERVED = 'reserved', 'Reserved'
        SOLD = 'sold', 'Sold'
        ARCHIVED = 'archived', 'Archived'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='advertisements',
    )
    title = models.CharField(max_length=180)
    description = models.TextField(max_length=5000)
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
    )
    currency = models.CharField(max_length=3, default='NGN')
    category = models.CharField(max_length=30, choices=Category.choices, default=Category.OTHER)
    condition = models.CharField(max_length=30, choices=Condition.choices, default=Condition.USED)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    location = models.CharField(max_length=160, blank=True)
    image = models.ImageField(upload_to='adverts/', blank=True, null=True)
    views_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'category', '-created_at']),
            models.Index(fields=['user', 'status', '-created_at']),
            models.Index(fields=['price']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(price__gte=0) | models.Q(price__isnull=True),
                name='marketplace_price_non_negative',
            ),
        ]

    def __str__(self):
        return self.title


class AdvertisementImage(models.Model):
    advertisement = models.ForeignKey(Advertisement, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='adverts/')
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['position', 'id']

    def __str__(self):
        return f'Image for {self.advertisement.title}'


class SavedAdvertisement(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_advertisements')
    advertisement = models.ForeignKey(Advertisement, on_delete=models.CASCADE, related_name='saved_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'advertisement'], name='unique_saved_advertisement'),
        ]


class Report(models.Model):
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='marketplace_reports')
    advertisement = models.ForeignKey(Advertisement, on_delete=models.CASCADE, related_name='reports')
    reason = models.TextField(max_length=1000)
    reported_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-reported_at']
        constraints = [
            models.UniqueConstraint(fields=['reporter', 'advertisement'], name='unique_marketplace_report'),
        ]

    def __str__(self):
        return f'Report by {self.reporter} on {self.advertisement.title}'


class Message(models.Model):
    """Deprecated marketplace conversation model kept for migration compatibility.

    New marketplace conversations use the main messaging application, which has
    participant authorization and realtime websocket delivery.
    """

    conversation_id = models.UUIDField(default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='advertisement_sent_messages')
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='advertisement_received_messages')
    advertisement = models.ForeignKey(Advertisement, on_delete=models.CASCADE, related_name='legacy_messages')
    content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Message from {self.sender} to {self.receiver} for {self.advertisement.title}'
