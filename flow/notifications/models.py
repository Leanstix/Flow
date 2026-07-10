from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Verb(models.TextChoices):
        MESSAGE = 'message', 'Message'
        LIKE = 'like', 'Like'
        COMMENT = 'comment', 'Comment'
        COMMENT_REPLY = 'comment_reply', 'Comment reply'
        REPOST = 'repost', 'Repost'
        FRIEND_REQUEST = 'friend_request', 'Friend request'
        FRIEND_ACCEPTED = 'friend_accepted', 'Friend accepted'
        SYSTEM = 'system', 'System'

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='notifications',
        on_delete=models.CASCADE,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='actor_notifications',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    verb = models.CharField(max_length=32, choices=Verb.choices, default=Verb.SYSTEM)
    message = models.TextField(blank=True)
    target_post = models.ForeignKey(
        'posts.Post',
        related_name='notifications',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    target_comment = models.ForeignKey(
        'posts.Comment',
        related_name='notifications',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    target_conversation = models.ForeignKey(
        'messaging.Conversation',
        related_name='notifications',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', '-created_at']),
            models.Index(fields=['verb', '-created_at']),
        ]

    def __str__(self):
        return f'{self.verb} notification for {self.recipient_id}'
