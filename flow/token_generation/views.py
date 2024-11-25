from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
import logging

logger = logging.getLogger(__name__)

class GenerateAccessTokenView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            auth_header = request.headers.get("Authorization")
            logger.info("Authorization header: %s", auth_header)

            if not auth_header or not auth_header.startswith("Bearer "):
                return Response({"error": "Refresh token missing or invalid."}, status=status.HTTP_400_BAD_REQUEST)

            refresh_token = auth_header.split(" ")[1]
            logger.info("Refresh token: %s", refresh_token)

            refresh = RefreshToken(refresh_token)  # Validate refresh token
            access_token = str(refresh.access_token)

            return Response({"access": access_token}, status=status.HTTP_200_OK)

        except TokenError as e:
            logger.error("Token error: %s", str(e))
            return Response({"error": "Invalid or expired refresh token."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("Unexpected error: %s", str(e))
            return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)