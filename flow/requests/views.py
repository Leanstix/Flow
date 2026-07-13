from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.models import Notification
from notifications.services import create_notification

from .models import FriendRequest
from .serializers import FriendRequestSerializer, FriendSerializer, UserSerializer

User = get_user_model()


def active_users_for_mentions(request_user, query=''):
    query = (query or '').strip().lstrip('@')[:80]
    base = User.objects.filter(is_active=True).exclude(id=request_user.id).exclude(user_name__isnull=True).exclude(user_name='')

    friends = base.filter(
        Q(sent_requests__to_user=request_user, sent_requests__accepted=True)
        | Q(received_requests__from_user=request_user, received_requests__accepted=True)
    ).distinct()
    if query:
        friends = friends.filter(
            Q(user_name__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
        )
    friends = list(friends.order_by('user_name')[:20])
    if friends:
        return friends

    users = base
    if query:
        users = users.filter(
            Q(user_name__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
        )
    return list(users.order_by('user_name')[:20])


class SearchUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        context = request.query_params.get('context', '').strip().lower()

        if context == 'mention':
            users = active_users_for_mentions(request.user, query)
            serializer = UserSerializer(users, many=True, context={'request': request, 'mention_context': True})
            return Response(serializer.data, status=status.HTTP_200_OK)

        if not query:
            return Response({'error': "Query parameter 'q' cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)

        users = User.objects.filter(
            is_active=True,
        ).filter(
            Q(user_name__icontains=query) | Q(email__icontains=query)
        ).exclude(id=request.user.id).order_by('user_name')[:50]

        serializer = UserSerializer(users, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class FriendRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        requests = FriendRequest.objects.filter(to_user=request.user, accepted=False)
        serializer = FriendRequestSerializer(requests, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        to_user_id = request.data.get('to_user_id')
        if not to_user_id:
            return Response({'error': "Missing 'to_user_id' in request body."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            to_user = User.objects.get(id=to_user_id, is_active=True)
        except User.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        if to_user == request.user:
            return Response({'error': 'You cannot send a friend request to yourself.'}, status=status.HTTP_400_BAD_REQUEST)

        friend_request, created = FriendRequest.objects.get_or_create(from_user=request.user, to_user=to_user)
        if not created:
            return Response({'error': 'Friend request already sent.'}, status=status.HTTP_400_BAD_REQUEST)

        create_notification(
            recipient=to_user,
            actor=request.user,
            verb=Notification.Verb.FRIEND_REQUEST,
            message=f'{request.user.user_name or request.user.email} sent you a friend request.',
        )
        return Response(
            FriendRequestSerializer(friend_request, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    def patch(self, request, pk):
        try:
            friend_request = FriendRequest.objects.get(id=pk, to_user=request.user)
        except FriendRequest.DoesNotExist:
            return Response({'error': 'Friend request not found.'}, status=status.HTTP_404_NOT_FOUND)

        friend_request.accepted = True
        friend_request.save(update_fields=['accepted'])
        create_notification(
            recipient=friend_request.from_user,
            actor=request.user,
            verb=Notification.Verb.FRIEND_ACCEPTED,
            message=f'{request.user.user_name or request.user.email} accepted your friend request.',
        )

        return Response(
            {
                'message': 'Friend request accepted.',
                'from_user_id': friend_request.from_user.id,
                'to_user_id': friend_request.to_user.id,
            },
            status=status.HTTP_200_OK,
        )


class ViewFriendsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        friends = User.objects.filter(
            Q(sent_requests__to_user=request.user, sent_requests__accepted=True)
            | Q(received_requests__from_user=request.user, received_requests__accepted=True)
        ).filter(is_active=True).distinct().order_by('user_name')

        serializer = FriendSerializer(friends, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
