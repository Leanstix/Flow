from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import FriendRequest
from .serializers import FriendRequestSerializer, UserSerializer

User = get_user_model()  # Dynamically load the user model

class SearchUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response({"error": "Query parameter 'q' cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)

        # Filter users based on their email
        users = User.objects.filter(email__icontains=query).exclude(id=request.user.id)
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class FriendRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Retrieve all friend requests sent to the authenticated user that are not yet accepted."""
        requests = FriendRequest.objects.filter(to_user=request.user, accepted=False)
        serializer = FriendRequestSerializer(requests, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """Send a friend request to another user."""
        to_user_id = request.data.get("to_user_id")
        if not to_user_id:
            return Response({"error": "Missing 'to_user_id' in request body."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            to_user = User.objects.get(id=to_user_id)
            if FriendRequest.objects.filter(from_user=request.user, to_user=to_user).exists():
                return Response({"error": "Friend request already sent."}, status=status.HTTP_400_BAD_REQUEST)
            
            friend_request = FriendRequest.objects.create(from_user=request.user, to_user=to_user)
            return Response(FriendRequestSerializer(friend_request).data, status=status.HTTP_201_CREATED)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

    def patch(self, request, pk):
        """Accept a friend request."""
        try:
            friend_request = FriendRequest.objects.get(id=pk, to_user=request.user)
            friend_request.accepted = True
            friend_request.save()
            return Response(FriendRequestSerializer(friend_request).data, status=status.HTTP_200_OK)
        except FriendRequest.DoesNotExist:
            return Response({"error": "Friend request not found."}, status=status.HTTP_404_NOT_FOUND)