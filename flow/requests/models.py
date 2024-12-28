from django.conf import settings
from django.db import models
from messaging.models import Conversation

class FriendRequest(models.Model):
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        related_name="sent_requests", 
        on_delete=models.CASCADE
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        related_name="received_requests", 
        on_delete=models.CASCADE
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    accepted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.from_user.user_name} -> {self.to_user.user_name}"
    