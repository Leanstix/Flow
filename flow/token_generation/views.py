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
            auth_header = request.headers.get("Authorization")
            logger.info("Authorization header: %s", auth_header)

            if not auth_header or not auth_header.startswith("Bearer "):
                logger.error("No Authorization header or invalid format.")
                return Response({"error": "Refresh token missing or invalid."}, status=status.HTTP_400_BAD_REQUEST)

            refresh_token = auth_header.split(" ")[1]
            logger.info("Refresh token received: %s", refresh_token)

            # Decode token to debug claims
            try:
                decoded_token = jwt.decode(refresh_token, options={"verify_signature": False})
                logger.info("Decoded refresh token claims: %s", decoded_token)
            except Exception as decode_error:
                logger.error("Error decoding token: %s", str(decode_error))

            # Validate refresh token and generate access token
            refresh = RefreshToken(refresh_token)
            if refresh.get("token_type") != "refresh":
                logger.error("Invalid token type: %s", refresh.get("token_type"))
                return Response({"error": "Invalid or expired refresh token."}, status=status.HTTP_400_BAD_REQUEST)

            access_token = str(refresh.access_token)
            logger.info("Generated access token: %s", access_token)

            return Response({"access": access_token}, status=status.HTTP_200_OK)

        except TokenError as e:
            logger.error("Token error: %s", str(e))
            return Response({"error": "Invalid or expired refresh token."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error("Unexpected error: %s", str(e))
            return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
