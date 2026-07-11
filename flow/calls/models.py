import uuid

from django.conf import settings
from django.db import models


class Room(models.Model):
    CALL_TYPES = (
        ('audio', 'Audio'),
        ('video', 'Video'),
    )
    STATUSES = (
        ('ringing', 'Ringing'),
        ('active', 'Active'),
        ('ended', 'Ended'),
        ('rejected', 'Rejected'),
        ('missed', 'Missed'),
    )

    room_name = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='created_call_rooms',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    conversation = models.ForeignKey(
        'messaging.Conversation',
        related_name='call_rooms',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    call_type = models.CharField(max_length=10, choices=CALL_TYPES, default='video')
    status = models.CharField(max_length=12, choices=STATUSES, default='active')
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='rooms')
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at'], name='call_room_status_idx'),
            models.Index(fields=['created_by', 'created_at'], name='call_room_creator_idx'),
        ]

    def __str__(self):
        return self.room_name


class CallInvitation(models.Model):
    STATUSES = (
        ('ringing', 'Ringing'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('left', 'Left'),
    )

    room = models.ForeignKey(Room, related_name='invitations', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='call_invitations', on_delete=models.CASCADE)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='sent_call_invitations',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    status = models.CharField(max_length=10, choices=STATUSES, default='ringing')
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['room', 'user'], name='unique_call_room_invitee'),
        ]
        indexes = [
            models.Index(fields=['user', 'status', 'created_at'], name='call_invitee_status_idx'),
        ]

    def __str__(self):
        return f'{self.user_id} in {self.room_id}: {self.status}'
