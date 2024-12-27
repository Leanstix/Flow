from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import FriendRequest, Conversation
from .serializers import FriendRequestSerializer, UserSerializer, FriendSerializer
from django.db.models import Q

User = get_user_model()

class SearchUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response({"error": "Query parameter 'q' cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)

        users = User.objects.filter(
            Q(user_name__icontains=query) | Q(email__icontains=query)
        ).exclude(id=request.user.id)

        serializer = UserSerializer(users, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

class FriendRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        requests = FriendRequest.objects.filter(to_user=request.user, accepted=False)
        serializer = FriendRequestSerializer(requests, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
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
        try:
            friend_request = FriendRequest.objects.get(id=pk, to_user=request.user)
            friend_request.accepted = True
            friend_request.save()

            # Prepare response data
            response_data = {
                "message": "Friend request accepted.",
                "from_user_id": friend_request.from_user.id,
                "to_user_id": friend_request.to_user.id,
            }

            return Response(response_data, status=status.HTTP_200_OK)
        except FriendRequest.DoesNotExist:
            return Response({"error": "Friend request not found."}, status=status.HTTP_404_NOT_FOUND)

class ViewFriendsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        friends = User.objects.filter(
            Q(sent_requests__to_user=request.user, sent_requests__accepted=True) |
            Q(received_requests__from_user=request.user, received_requests__accepted=True)
        ).distinct()

        serializer = FriendSerializer(friends, many=True, context={"request": request}) 
        return Response(serializer.data, status=status.HTTP_200_OK)
