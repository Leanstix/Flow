from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import UserProfileSerializer

User = get_user_model()

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise NotFound("User not found")

        # Generate tokens
        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        # Serialize user data
        serializer = UserProfileSerializer(user)
        user_data = serializer.data

        # Include tokens and mandatory fields
        response_data = {
            "user_id": user.id,
            "email": user.email,
        }

        # Combine with serialized optional fields
        response_data.update(user_data)
        
        return Response(response_data)
