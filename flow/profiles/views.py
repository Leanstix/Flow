from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from rest_framework.exceptions import NotFound
from .serializers import UserProfileSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from rest_framework.exceptions import NotFound
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import UserProfileSerializer

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise NotFound("User not found")

        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        serializer = UserProfileSerializer(user)
        user_data = serializer.data

        response_data = {
            "user_id": user.id,
            "email": user.email,
        }

        response_data.update(user_data)
        
        return Response(response_data)

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise NotFound("User not found")
        
        serializer = UserProfileSerializer(user)
        return Response(serializer.data)
