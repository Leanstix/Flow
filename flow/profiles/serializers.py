from django.contrib.auth import get_user_model
from rest_framework import serializers


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = [
            'id',
            'email',
            'gender',
            'phone_number',
            'university_id',
            'university_name',
            'department',
            'faculty',
            'bio',
            'first_name',
            'last_name',
            'user_name',
            'year_of_study',
            'profile_picture',
            'is_staff',
            'is_superuser',
            'email_verified',
        ]
        read_only_fields = fields
