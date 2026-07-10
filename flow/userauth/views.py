import logging

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.generics import UpdateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .cloudinary_utils import upload_profile_picture
from .emails import ActivationEmailError
from .serializers import (
    ChangePasswordSerializer,
    UserActivationSerializer,
    UserProfileUpdateSerializer,
    UserRegistrationSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()

class UserRegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            try:
                serializer.save()
            except ActivationEmailError:
                logger.exception('Registration failed because the activation email was not sent')
                return Response(
                    {'error': 'We could not send the activation email. Please try again.'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            return Response({"message": "Account created successfully! Please check your email to activate your account."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserActivationView(APIView):
    permission_classes = [AllowAny]  # This allows unauthenticated users to access this endpoint

    def post(self, request):
        serializer = UserActivationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Account activated successfully!"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class UserProfileUpdateView(UpdateAPIView):
    serializer_class = UserProfileUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        logger.info("Updating profile for user: %s", user.email)
        data = request.data.copy()

        # Check if a new profile picture is uploaded
        profile_picture = request.FILES.get('profile_picture')
        if profile_picture:
            logger.info("New profile picture uploaded: %s", profile_picture.name)
            try:
                cloudinary_url = upload_profile_picture(profile_picture)
                logger.info("Profile picture uploaded to Cloudinary: %s", cloudinary_url)
                data['profile_picture'] = cloudinary_url
            except Exception as exc:
                logger.exception("Error uploading profile picture to Cloudinary")
                return Response(
                    {'error': f'Error uploading profile picture: {exc}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        # Update other fields
        serializer = self.get_serializer(user, data=data, partial=True)
        if serializer.is_valid():
            self.perform_update(serializer)
            logger.info("Profile updated successfully")
            return Response(serializer.data)
        else:
            logger.error(f"Serializer errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class ActivateAccountView(APIView):
    def get(self, request):
        token = request.query_params.get('token')
        try:
            user = User.objects.get(activation_token=token)
            user.activate_account()  # Activate the account and clear the token
            return Response({"message": "Account activated successfully!"})
        except User.DoesNotExist:
            return Response({"error": "Invalid or expired activation token."}, status=400)

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Password changed successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
