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
    
User = get_user_model()

class UserProfileUpdateView(UpdateAPIView):
    serializer_class = UserProfileUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        # Allow only the authenticated user to update their own profile
        return self.request.user

    def update(self, request, *args, **kwargs):
        user = self.get_object()

        # Check if a file is included in the request
        profile_image = request.FILES.get('profile_image')
        if profile_image:
            try:
                # Upload the file directly to Google Drive
                drive_url = upload_file_to_drive(profile_image, profile_image.name)
                # Save the URL to the user's profile
                user.profile_image_url = drive_url
                user.save()

            except Exception as e:
                return Response({'error': f'Error uploading file: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return super().update(request, *args, **kwargs)

        # Proceed with updating other fields using the serializer
        serializer = self.get_serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(serializer.data, status=status.HTTP_200_OK)
    
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
