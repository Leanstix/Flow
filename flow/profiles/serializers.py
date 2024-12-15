from rest_framework import serializers
from django.conf import settings
from django.contrib.auth import get_user_model  # Use this for the custom user model

class UserProfileSerializer(serializers.ModelSerializer):
    profile_picture = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()  # Dynamically use the custom user model
        fields = [
            "id", "email", "gender", "phone_number", "university_id", 
            "department", "bio", "first_name", "last_name", "user_name", 
            "year_of_study", "profile_picture",
        ]

    def get_profile_picture(self, obj):
        if obj.profile_picture:
            return f"{settings.MEDIA_URL}{obj.profile_picture}"
        return None
