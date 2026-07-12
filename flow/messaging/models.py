from django.conf import settings
from django.db import models


class Conversation(models.Model):
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        names = [participant.user_name or participant.email for participant in self.participants.all()]
        return f"Conversation between {', '.join(names)}"


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='sent_messages', on_delete=models.CASCADE)
    reply_to = models.ForeignKey(
        'self',
        related_name='replies',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    content = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['conversation', 'timestamp'], name='msg_conversation_time_idx'),
            models.Index(fields=['sender', 'timestamp'], name='msg_sender_time_idx'),
        ]

    @property
    def is_deleted(self):
        return self.deleted_at is not None

    def __str__(self):
        return f'Message from {self.sender} at {self.timestamp}'


class MessageAttachment(models.Model):
    class Kind(models.TextChoices):
        IMAGE = 'image', 'Photo'
        VIDEO = 'video', 'Video'
        AUDIO = 'audio', 'Audio'
        DOCUMENT = 'document', 'Document'
        CONTACT = 'contact', 'Contact'
        LOCATION = 'location', 'Location'
        LISTING = 'listing', 'Marketplace listing'

    message = models.ForeignKey(Message, related_name='attachments', on_delete=models.CASCADE)
    kind = models.CharField(max_length=20, choices=Kind.choices)
    url = models.URLField(max_length=1200, blank=True)
    thumbnail_url = models.URLField(max_length=1200, blank=True)
    public_id = models.CharField(max_length=500, blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    mime_type = models.CharField(max_length=120, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    duration_seconds = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    position = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['position', 'id']
        indexes = [models.Index(fields=['message', 'position'], name='msg_attachment_order_idx')]

    def __str__(self):
        return f'{self.kind} attachment for message {self.message_id}'


class MessageReceipt(models.Model):
    message = models.ForeignKey(Message, related_name='receipts', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='message_receipts', on_delete=models.CASCADE)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['message', 'user'], name='unique_message_receipt'),
        ]
        indexes = [
            models.Index(fields=['user', 'delivered_at'], name='receipt_user_delivery_idx'),
            models.Index(fields=['user', 'read_at'], name='receipt_user_read_idx'),
        ]

    def __str__(self):
        return f'Receipt for message {self.message_id} by user {self.user_id}'
