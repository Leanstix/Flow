import os
from PIL import Image  # Import Pillow
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, Group, Permission
from django.core.validators import RegexValidator, EmailValidator
from django.utils.crypto import get_random_string
from django.conf import settings
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from .drive_utils import upload_file_to_drive
import logging
import requests
from io import BytesIO
import json
import os

class CustomUserManager(BaseUserManager):
    def create(self, validated_data):
        try:
            # Extracting necessary fields
            email = validated_data['email']
            university_id = validated_data['university_id']
            password = validated_data['password']

            # Create the user
            user = User.objects.create_user(
                email=email,
                university_id=university_id,
                password=password,
                **{k: v for k, v in validated_data.items() if k not in ['email', 'university_id', 'password']}
            )

            # Log user creation success
            logger.info(f"User created successfully: {email}")

            # Send activation email
            activation_link = f"{settings.FRONTEND_URL}/activate/{user.activation_token}"
            subject = "Account Activation"
            message = f"Hi {email},\n\nPlease activate your account using the link below:\n{activation_link}\n\nThank you!"

            # Log email attempt
            logger.info(f"Sending activation email to {email}")
            
            email_from = os.environ.get('EMAIL_HOST_USER')
            if not email_from:
                raise ValueError("EMAIL_HOST_USER environment variable is not set.")
            
            send_mail(
                subject=subject,
                message=message,
                from_email=email_from,
                recipient_list=[email],
                fail_silently=False,
            )

            # Log email success
            logger.info(f"Activation email sent successfully to {email}")

            return user

        except Exception as e:
            logger.error(f"Error during user registration: {e}")
            raise ValidationError(f"An error occurred: {str(e)}")

    def create_superuser(self, email, university_id, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, university_id, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female')]
    YEAR_CHOICES = [(str(i), str(i)) for i in range(1, 7)]

    email = models.EmailField(unique=True, validators=[EmailValidator()])
    first_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50, blank=True, null=True)
    user_name = models.CharField(max_length=50, blank=True, null=True, unique=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    phone_number = models.CharField(
        max_length=15,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$')],
        blank=True,
        null=True,
        unique=True
    )

    university_id = models.CharField(max_length=100, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    year_of_study = models.CharField(max_length=1, choices=YEAR_CHOICES, blank=True, null=True)

    bio = models.TextField(blank=True, null=True)
    profile_picture = models.URLField(blank=True, null=True)  # Store Google Drive URL

    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    activation_token = models.CharField(max_length=32, blank=True, null=True)
    email_verified = models.BooleanField(default=False)

    groups = models.ManyToManyField(Group, related_name="userauth_users", blank=True)
    user_permissions = models.ManyToManyField(Permission, related_name="userauth_users_permissions", blank=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['university_id'] 

    def __str__(self):
        return f"{self.email}"

    def save(self, *args, **kwargs):
        if not self.pk and not self.activation_token and not self.email_verified:
            self.activation_token = get_random_string(32)
        super().save(*args, **kwargs)
        '''
        if self.profile_picture:
            self.resize_profile_picture()'''
    '''
    def resize_profile_picture(self):
        """Resize the profile picture and upload it to Google Drive."""
        temp_file_path = None  # Ensure it's defined

        try:
            # Check if the profile picture is already a Drive link
            if isinstance(self.profile_picture, str) and self.profile_picture.startswith("http"):
                logging.info("Skipping resizing: profile picture is an external link.")
                return

            # Load the image from a local path
            if not self.profile_picture or not hasattr(self.profile_picture, 'path'):
                logging.error("Profile picture file path is invalid.")
                return

            img = Image.open(self.profile_picture.path)

            # Resize if needed
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.thumbnail((400, 400))

            # Convert image to bytes
            temp_buffer = BytesIO()
            img.save(temp_buffer, format='JPEG', optimize=True, quality=85)
            temp_buffer.seek(0)

            # Save the resized image temporarily
            temp_file_path = f"/tmp/{os.path.basename(self.profile_picture.name)}"
            with open(temp_file_path, 'wb') as temp_file:
                temp_file.write(temp_buffer.read())

            # Upload to Google Drive
            shared_link = upload_file_to_drive(temp_file_path, os.path.basename(temp_file_path))
            if shared_link:
                self.profile_picture = shared_link
                self.save(update_fields=['profile_picture'])

        except Exception as e:
            logging.error(f"Error processing image: {e}")

        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
    '''
    def activate_account(self):
        """Activate the user's account."""
        self.is_active = True
        self.email_verified = True
        self.activation_token = None
        self.save(update_fields=['is_active', 'email_verified', 'activation_token'])


class Interest(models.Model):
    """Model to store user interests for feed customization."""
    name = models.CharField(max_length=500, unique=True)

    def __str__(self):
        return self.name
