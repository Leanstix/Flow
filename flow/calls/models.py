# models.py
from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()

class Room(models.Model):
    room_name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    participants = models.ManyToManyField(User, related_name="rooms")

    def __str__(self):
        return self.room_name
