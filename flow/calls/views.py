from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes
from rest_framework.status import HTTP_200_OK, HTTP_404_NOT_FOUND, HTTP_405_METHOD_NOT_ALLOWED
from .models import Room
import uuid

class CreateRoomView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        room_name = str(uuid.uuid4())
        room = Room.objects.create(room_name=room_name)
        room.participants.add(request.user)
        return Response({"room_name": room_name, "message": "Room created successfully"}, status=HTTP_200_OK)


class JoinRoomView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, room_name):
        try:
            room = Room.objects.get(room_name=room_name)
            if request.user not in room.participants.all():
                room.participants.add(request.user)
            return Response({"message": "Joined room successfully"}, status=HTTP_200_OK)
        except Room.DoesNotExist:
            return Response({"error": "Room does not exist"}, status=HTTP_404_NOT_FOUND)
