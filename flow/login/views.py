import logging

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import LoginSerializer

logger = logging.getLogger(__name__)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        user_data = {
            'refresh': str(refresh),
            'access': str(access),
            'user_id': user.id,
            'id': user.id,
            'email': user.email,
            'gender': user.gender,
            'phone_number': user.phone_number,
            'university_id': user.university_id,
            'university_name': user.university_name,
            'department': user.department,
            'faculty': user.faculty,
            'bio': user.bio,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'user_name': user.user_name,
            'year_of_study': user.year_of_study,
            'profile_picture': user.profile_picture or None,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'email_verified': user.email_verified,
        }

        return Response(user_data, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response({'error': 'Refresh token missing.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            RefreshToken(refresh_token)
        except TokenError:
            return Response({'error': 'Invalid or expired refresh token.'}, status=status.HTTP_400_BAD_REQUEST)

        # Stateless JWTs remain valid until expiry unless the blacklist app is
        # installed. The client always removes both tokens on this response.
        logger.info('Successfully logged out user.')
        return Response({'message': 'Successfully logged out.'}, status=status.HTTP_200_OK)
