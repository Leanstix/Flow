import os

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, Group, Permission
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator, RegexValidator
from django.db import models
from django.utils.crypto import get_random_string


class CustomUserManager(BaseUserManager):
    """Custom manager for Flow users.

    The previous implementation overrode ``create`` with a serializer-shaped
    signature and then called an undefined ``create_user`` from
    ``create_superuser``. That broke Django's normal user creation APIs,
    tests, fixtures, and createsuperuser.
    """

    def create_user(self, email, university_id=None, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")

        email = self.normalize_email(email)
        user = self.model(email=email, university_id=university_id, **extra_fields)

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_superuser(self, email, university_id, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('email_verified', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, university_id, password, **extra_fields)

    def create(self, *args, **kwargs):
        """Keep backward compatibility with older serializer-style calls.

        Some early code used ``User.objects.create(validated_data)``. Normal
        Django code uses ``User.objects.create(email=..., password=...)``. This
        supports both while ensuring passwords are always hashed.
        """
        if args and len(args) == 1 and isinstance(args[0], dict):
            data = args[0].copy()
            password = data.pop('password', None)
            return self.create_user(password=password, **data)

        if 'password' in kwargs:
            password = kwargs.pop('password')
            return self.create_user(password=password, **kwargs)

        return super().create(*args, **kwargs)


class User(AbstractBaseUser, PermissionsMixin):
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female')]
    YEAR_CHOICES = [(str(i), str(i)) for i in range(1, 7)]

    email = models.EmailField(unique=True, validators=[EmailValidator()])
    first_name = models.CharField(max_length=50, blank=True, null=True)
    last_name = models.CharField(max_length=50, blank=True, null=True)
    user_name = models.CharField(max_length=50, blank=True, null=True, unique=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)
    phone_number = models.CharField(
        max_length=15,
        validators=[RegexValidator(regex=r'^\+?1?\d{9,15}$')],
        blank=True,
        null=True,
        unique=True,
    )

    university_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    university_name = models.CharField(max_length=255, blank=True, null=True)
    department = models.CharField(max_length=255, blank=True, null=True)
    faculty = models.CharField(max_length=255, blank=True, null=True)
    year_of_study = models.CharField(max_length=1, choices=YEAR_CHOICES, blank=True, null=True)

    bio = models.TextField(blank=True, null=True, max_length=250)
    profile_picture = models.URLField(blank=True, null=True)
    interests = models.ManyToManyField('Interest', related_name='interested_users', blank=True)

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
        return self.email

    def save(self, *args, **kwargs):
        if not self.pk and not self.activation_token and not self.email_verified:
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
    name = models.CharField(max_length=500, unique=True)

    def __str__(self):
        return self.name
