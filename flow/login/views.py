from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
import logging
from .serializers import LoginSerializer
from django.conf import settings

logger = logging.getLogger(__name__)

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        print(request.data)
        serializer = LoginSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access = refresh.access_token
            
            # Dynamically build response with only available user fields
            user_data = {
                "refresh": str(refresh),
                "access": str(access),
                "user_id": user.id,
                "email": user.email,
            }
            
            # Optional fields
            optional_fields = {
                "gender": getattr(user, "gender", None),
                "phone_number": getattr(user, "phone_number", None),
                "university_id": getattr(user, "university_id", None),
                "department": getattr(user, "department", None),
                "bio": getattr(user, "bio", None),
                "first_name": getattr(user, "first_name", None),
                "last_name": getattr(user, "last_name", None),
                "user_name": getattr(user, "user_name", None),
                "year_of_study": getattr(user, "year_of_study", None),
                "user_name": getattr(user, "user_name", None),
                "profile_picture": (
                    f"{user.profile_picture}" 
                    if user.profile_picture 
                    else None
                ),
            }
            
            # Filter out None values
            user_data.update({k: v for k, v in optional_fields.items() if v is not None})
            
            return Response(user_data, status=status.HTTP_200_OK)
        else:
            # Logging serializer errors for debugging
            logger.error("Login validation failed: %s", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            # Get the refresh token from the request body
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                logger.error("No refresh token provided.")
                return Response({"error": "Refresh token missing."}, status=status.HTTP_400_BAD_REQUEST)

            # Validate the refresh token
            token = RefreshToken(refresh_token)

            # Blacklist the token (if blacklisting is enabled)
            # token.blacklist()

            logger.info("Successfully logged out user.")
            return Response({"message": "Successfully logged out."}, status=status.HTTP_200_OK)

        except TokenError as e:
            logger.error("Token error during logout: %s", str(e))
            return Response({"error": "Invalid or expired refresh token."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("Unexpected error during logout: %s", str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
