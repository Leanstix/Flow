import os  # Add this import
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import UserRegistrationSerializer, UserActivationSerializer, UserProfileUpdateSerializer, ChangePasswordSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import UpdateAPIView
from django.contrib.auth import get_user_model
from rest_framework.permissions import AllowAny
from .models import User
from .drive_utils import upload_file_to_drive
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class UserRegistrationView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Account created successfully! Please check your email to activate your account."}, status=status.HTTP_201_CREATED)
        else:
            print(serializer.errors)
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
        logger.info(f"Updating profile for user: {user.email}")

        # Check if a new profile picture is uploaded
        profile_picture = request.FILES.get('profile_picture')
        if profile_picture:
            logger.info(f"New profile picture uploaded: {profile_picture.name}")
            try:
                # Upload to Google Drive and store the link
                drive_url = upload_file_to_drive(profile_picture, profile_picture.name)
                logger.info(f"Profile picture uploaded to Google Drive: {drive_url}")
                user.profile_picture = drive_url
                user.save(update_fields=['profile_picture'])
            except Exception as e:
                logger.error(f"Error uploading profile picture: {str(e)}")
                return Response({'error': f'Error uploading profile picture: {str(e)}'},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Update other fields
        serializer = self.get_serializer(user, data=request.data, partial=True)
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
