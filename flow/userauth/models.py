import os
from PIL import Image  # Import Pillow
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, Group, Permission
from django.core.validators import RegexValidator, EmailValidator
from django.utils.crypto import get_random_string
from django.conf import settings


class CustomUserManager(BaseUserManager):
    def create_user(self, email, university_id, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be filled")
        if not university_id:
            raise ValueError("The University ID field must be filled")

        email = self.normalize_email(email)
        user = self.model(
            email=email,
            university_id=university_id,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, university_id, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, university_id, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    # Constants for choices
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female')]
    YEAR_CHOICES = [(str(i), str(i)) for i in range(1, 7)]  # e.g., 1st to 6th year

    # Basic Information
    email = models.EmailField(unique=True, validators=[EmailValidator()])
    first_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50, blank=True, null=True)
    user_name = models.CharField(max_length=50, blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    phone_number = models.CharField(
        max_length=15,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$')],
        blank=True,
        null=True,
        help_text="Phone number format: +999999999. Up to 15 digits."
    )

    # University Details
    university_id = models.CharField(max_length=6, unique=True, help_text="University ID number")
    department = models.CharField(max_length=100, blank=True, null=True)
    year_of_study = models.CharField(max_length=1, choices=YEAR_CHOICES, blank=True, null=True)

    # Profile Details
    bio = models.TextField(blank=True, help_text="Brief bio or description", null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    interests = models.ManyToManyField('Interest', blank=True, related_name="interested_users")

    # Account Status
    is_active = models.BooleanField(default=False)  # Account activation via email
    is_staff = models.BooleanField(default=False)   # Staff status for admin access
    activation_token = models.CharField(max_length=32, blank=True, null=True)
    email_verified = models.BooleanField(default=False)

    # Adding related_name to avoid clashes
    groups = models.ManyToManyField(
        Group,
        related_name="userauth_users",  # Custom related_name
        blank=True
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="userauth_users_permissions",  # Custom related_name
        blank=True
    )

    # Managers
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
            self.resize_profile_picture()

    def resize_profile_picture(self):
        """Resize the profile picture to a standard size and optimize it."""
        picture_path = self.profile_picture.path
        try:
            with Image.open(picture_path) as img:
                # Ensure the image is in RGB format
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                # Resize and optimize
                img.thumbnail((300, 300))
                img.save(picture_path, format='JPEG', optimize=True, quality=85)
        except Exception as e:
            print(f"Error processing image: {e}")

    def activate_account(self):
        """Activate the user's account."""
        self.is_active = True
        self.email_verified = True
        self.activation_token = None
        self.save(update_fields=['is_active', 'email_verified', 'activation_token'])


class Interest(models.Model):
    """Model to store user interests for feed customization."""
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name
