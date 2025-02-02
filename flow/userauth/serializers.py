from rest_framework import serializers
from django.contrib.auth import get_user_model
#from django.core.mail import send_mail
from django.conf import settings
from .models import Interest
from django.core.mail import send_mail
from dotenv import load_dotenv
import os

User = get_user_model()

class InterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interest
        fields = ['id', 'name']

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'university_id', 'password']

    def create(self, validated_data):
        # Pop password from validated_data
        password = validated_data.pop('password')

        # Create user instance
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        Email = os.environ.get('EMAIL_HOST_USER')

       #sending an email to the user to receive their activation link
        activation_url = f"https://flow-aleshinloye-olamilekan-s-projects.vercel.app/activate?token={user.activation_token}"
        send_mail(
            "Flow User Activation",#subject
            f"click on the link to activate your account {activation_url}",#message
            Email, #from email
            [user.email], #toemail
            fail_silently=False
        )
        print(f"Activation link (copy and paste in browser to activate): {activation_url}")

        return user

class UserActivationSerializer(serializers.Serializer):
    token = serializers.CharField()

    def validate_token(self, value):
        try:
            user = User.objects.get(activation_token=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid or expired activation token.")
        return value

    def save(self):
        token = self.validated_data['token']
        user = User.objects.get(activation_token=token)
        user.activate_account()  # Activate the account and clear the token
        return user

class UserProfileUpdateSerializer(serializers.ModelSerializer):
    interests = serializers.PrimaryKeyRelatedField(queryset=Interest.objects.all(), many=True, required=False)
    profile_picture = serializers.URLField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'gender', 'phone_number', 'department',
            'year_of_study', 'bio', 'profile_picture', 'interests', 'user_name'
        ]
        read_only_fields = ['email', 'university_id']  # Prevent changes to email and university_id

    def validate_profile_picture(self, value):
        """
        Custom validation for the profile_picture field.
        Ensures that the URL is a valid Google Drive URL.
        """
        if value:  # Only validate if a value is provided
            if not value.startswith("https://drive.google.com/file/d/"):
                raise serializers.ValidationError("Invalid Google Drive URL. The URL must start with 'https://drive.google.com/file/d/'.")
        return value

    def update(self, instance, validated_data):
        interests = validated_data.pop('interests', None)
        instance = super().update(instance, validated_data)

        # Update interests if provided
        if interests is not None:
            instance.interests.set(interests)  # Use .set() for many-to-many relationships

        return instance

class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value):
        # Add password validation rules if necessary
        if len(value) < 8:
            raise serializers.ValidationError("The new password must be at least 8 characters long.")
        return value

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user
        