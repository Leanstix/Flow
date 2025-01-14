from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from .models import Room
import uuid

@csrf_exempt
@login_required
def create_room(request):
    if request.method == "POST":
        room_name = str(uuid.uuid4())
        room = Room.objects.create(room_name=room_name)
        room.participants.add(request.user)
        return JsonResponse({"room_name": room_name, "message": "Room created successfully"})
    return JsonResponse({"error": "Invalid request method"}, status=405)

@csrf_exempt
@login_required
def join_room(request, room_name):
    if request.method == "POST":
        try:
            room = Room.objects.get(room_name=room_name)
            if request.user not in room.participants.all():
                room.participants.add(request.user)
            return JsonResponse({"message": "Joined room successfully"})
        except Room.DoesNotExist:
            return JsonResponse({"error": "Room does not exist"}, status=404)
    return JsonResponse({"error": "Invalid request method"}, status=405)


