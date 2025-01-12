from django.http import JsonResponse
import uuid

def create_room(request):
    room_name = str(uuid.uuid4())  # Generate a unique room name
    return JsonResponse({"room_name": room_name})