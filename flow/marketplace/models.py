from django.conf import settings
from django.db import models
import uuid

class Advertisement(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="advertisements")
    title = models.CharField(max_length=255)
    description = models.TextField()
    price = models.CharField(max_length=8, blank=True, null=True)
    image = models.ImageField(upload_to="adverts/", height_field=None, width_field=None, blank=True, null=True)  # Updated field name
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class AdvertisementImage(models.Model):
    advertisement = models.ForeignKey(Advertisement, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="adverts/")

    def __str__(self):
        return f"Image for {self.advertisement.title}"

class Report(models.Model):
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports"
    )
    advertisement = models.ForeignKey(
        Advertisement, on_delete=models.CASCADE, related_name="reports"
    )
    reason = models.TextField()
    reported_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report by {self.reporter} on {self.advertisement.title}"

class Message(models.Model):
    conversation_id = models.UUIDField(default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="advertisement_sent_messages"
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="advertisement_received_messages"
    )
    advertisement = models.ForeignKey(
        Advertisement, on_delete=models.CASCADE, related_name="messages"
    )
    content = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.sender} to {self.receiver} for {self.advertisement.title}"

