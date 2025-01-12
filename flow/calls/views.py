# views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import Room
import uuid

@csrf_exempt
@login_required
def create_room(request):
    room_name = str(uuid.uuid4())  # Generate a unique room name
    room = Room.objects.create(room_name=room_name)
    room.participants.add(request.user)  # Add the creator as a participant
    return JsonResponse({"room_name": room_name, "message": "Room created successfully"})
