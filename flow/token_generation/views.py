from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
import jwt
import logging

logger = logging.getLogger(__name__)

class GenerateAccessTokenView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            # Get the refresh token from the request body
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                logger.error("No refresh token provided.")
                return Response({"error": "Refresh token missing."}, status=status.HTTP_400_BAD_REQUEST)

            # Validate refresh token and generate a new access token
            refresh = RefreshToken(refresh_token)
            access_token = str(refresh.access_token)
            logger.info("Generated new access token for user ID %s", refresh.payload.get("user_id"))

            return Response({"access": access_token}, status=status.HTTP_200_OK)

        except TokenError as e:
            logger.error("Token error: %s", str(e))
            return Response({"error": "Invalid or expired refresh token."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("Unexpected error: %s", str(e))
            return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            