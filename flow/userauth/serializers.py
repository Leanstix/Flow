from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from .models import Interest

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

       # Print activation link in terminal for testing instead of sending an email
        activation_url = f"http://localhost:3000/activate?token={user.activation_token}"
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

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'gender', 'phone_number', 'department',
            'year_of_study', 'bio', 'profile_picture', 'interests'
        ]
        read_only_fields = ['email', 'university_id']  # Prevent changes to email and university_id

    def update(self, instance, validated_data):
        interests = validated_data.pop('interests', None)
        instance = super().update(instance, validated_data)

        # Update interests if provided
        if interests is not None:
            instance.interests.set(interests)

        instance.save()
        return instance
