from django.contrib.auth.models import User
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import smart_bytes, smart_str, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.core.mail import send_mail
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import os
from django.contrib.auth.hashers import make_password

token_generator = PasswordResetTokenGenerator()

class PasswordResetRequestView(APIView):
    def post(self, request):
        email = request.data.get("email")
        try:
            user = User.objects.get(email=email)
            token = token_generator.make_token(user)
            uidb64 = urlsafe_base64_encode(smart_bytes(user.id))
            reset_link = f"https://flow-aleshinloye-olamilekan-s-projects.vercel.app/reset?uid={uidb64}&token={token}"
            Email = os.environ.get('EMAIL_HOST_USER')

            # Send email
            send_mail(
                subject="Password Reset Request",
                message=f"Click the link to reset your password: {reset_link}",
                from_email=Email,
                recipient_list=[user.email],
            )
            return Response({"message": "Password reset link sent."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "User with this email does not exist."}, status=status.HTTP_404_NOT_FOUND)

class PasswordResetVerifyView(APIView):
    def post(self, request):
        uidb64 = request.data.get("uid")
        token = request.data.get("token")
        try:
            user_id = smart_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(id=user_id)

            if token_generator.check_token(user, token):
                return Response({"message": "Token is valid."}, status=status.HTTP_200_OK)
            return Response({"error": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)
        except DjangoUnicodeDecodeError:
            return Response({"error": "Invalid token format."}, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetCompleteView(APIView):
    def post(self, request):
        uidb64 = request.data.get("uid")
        token = request.data.get("token")
        new_password = request.data.get("password")

        try:
            user_id = smart_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(id=user_id)

            if token_generator.check_token(user, token):
                user.password = make_password(new_password)
                user.save()
                return Response({"message": "Password has been reset successfully."}, status=status.HTTP_200_OK)
            return Response({"error": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)
        except DjangoUnicodeDecodeError:
            return Response({"error": "Invalid token format."}, status=status.HTTP_400_BAD_REQUEST)