import random
import string
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator, EmailValidator
from django.utils.crypto import get_random_string

class CustomUserManager(BaseUserManager):
    def create_user(self, email, first_name, last_name, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be filled")

        email = self.normalize_email(email)
        user = self.model(
            email=email,
            first_name=first_name,
            last_name=last_name,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, first_name, last_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(email, first_name, last_name, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    # Constants for choices
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female'), ('O', 'Other')]
    YEAR_CHOICES = [(str(i), str(i)) for i in range(1, 7)]  # e.g., 1st to 6th year
    
    # Basic Information
    email = models.EmailField(unique=True, validators=[EmailValidator()])
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    phone_number = models.CharField(
        max_length=15,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$')],
        blank=True,
        help_text="Phone number format: +999999999. Up to 15 digits."
    )

    # University Details
    university_id = models.CharField(max_length=10, unique=True, help_text="University ID number")
    department = models.CharField(max_length=100)
    year_of_study = models.CharField(max_length=1, choices=YEAR_CHOICES)

    # Profile Details
    bio = models.TextField(blank=True, help_text="Brief bio or description")
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    interests = models.ManyToManyField('Interest', blank=True, related_name="interested_users")

    # Account Status
    is_active = models.BooleanField(default=False)  # Account activation via email
    is_staff = models.BooleanField(default=False)   # Staff status for admin access
    activation_token = models.CharField(max_length=32, blank=True, null=True)
    email_verified = models.BooleanField(default=False)

    # Managers
    objects = CustomUserManager()

    # Field definitions for Django auth
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'university_id']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    def save(self, *args, **kwargs):
        # Generate an activation token if the account is new and not yet verified
        if not self.activation_token and not self.email_verified:
            self.activation_token = get_random_string(32)
        super().save(*args, **kwargs)

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
