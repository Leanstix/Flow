import os
import logging
from io import BytesIO
from PIL import Image  # Import Pillow

from django.db import models, transaction
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, Group, Permission
from django.core.validators import RegexValidator, EmailValidator
from django.utils.crypto import get_random_string
from django.conf import settings
from django.core.mail import send_mail
from django.core.exceptions import ValidationError

from .drive_utils import upload_file_to_drive

logger = logging.getLogger(__name__)  # Setup logger


class CustomUserManager(BaseUserManager):
    def create(self, validated_data):
        try:
            email = validated_data['email']
            university_id = validated_data['university_id']
            password = validated_data['password']

            with transaction.atomic():  # Ensure atomicity
                user = User.objects.create_user(
                    email=email,
                    university_id=university_id,
                    password=password,
                    **{k: v for k, v in validated_data.items() if k not in ['email', 'university_id', 'password']}
                )

            logger.info(f"User created successfully: {email}")

            activation_link = f"{settings.FRONTEND_URL}/activate/{user.activation_token}"
            subject = "Account Activation"
            message = f"Hi {email},\n\nPlease activate your account using the link below:\n{activation_link}\n\nThank you!"

            email_from = os.getenv('EMAIL_HOST_USER')
            if not email_from:
                raise ValueError("EMAIL_HOST_USER environment variable is not set.")

            send_mail(
                subject=subject,
                message=message,
                from_email=email_from,
                recipient_list=[email],
                fail_silently=False,
            )

            logger.info(f"Activation email sent to {email}")
            return user

        except Exception as e:
            logger.error(f"Error during user registration: {e}")
            raise ValidationError(f"An error occurred: {str(e)}")

    def create_superuser(self, email, university_id, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if not extra_fields.get('is_staff'):
            raise ValueError("Superuser must have is_staff=True.")
        if not extra_fields.get('is_superuser'):
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
        help_text="Phone number format: +999999999. Up to 15 digits."
    )

    university_id = models.CharField(max_length=100, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    year_of_study = models.CharField(max_length=1, choices=YEAR_CHOICES, blank=True, null=True)

    bio = models.TextField(blank=True, help_text="Brief bio or description", null=True)
    profile_picture = models.URLField(blank=True, null=True)  # Store only the Google Drive link
    interests = models.JSONField('Interests', blank=True, null=True)

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
        if not self.pk:
            if not self.activation_token and not self.email_verified:
                self.activation_token = get_random_string(32)

        super().save(*args, **kwargs)

        if self.profile_picture:
            self.resize_and_upload_profile_picture()

    def resize_and_upload_profile_picture(self):
        """Resize profile picture and upload it to Google Drive."""
        try:
            # Ensure it's a valid image file
            if not self.profile_picture or isinstance(self.profile_picture, str) and self.profile_picture.startswith("http"):
                logger.info("Skipping resizing: Profile picture is already a Drive link.")
                return

            img = Image.open(self.profile_picture)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            img.thumbnail((400, 400))

            # Convert image to bytes
            temp_buffer = BytesIO()
            img.save(temp_buffer, format='JPEG', optimize=True, quality=85)
            temp_buffer.seek(0)

            # Upload to Google Drive
            drive_url = upload_file_to_drive(temp_buffer, f"profile_{self.pk}.jpg")
            if drive_url:
                self.profile_picture = drive_url
                self.save(update_fields=['profile_picture'])

        except Exception as e:
            logger.error(f"Error processing profile picture: {e}")

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
