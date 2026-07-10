from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Interest

User = get_user_model()


class InterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interest
        fields = ['id', 'name']


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ['email', 'university_id', 'password']

    def create(self, validated_data):
        password = validated_data.pop('password')
        return User.objects.create_user(password=password, **validated_data)


class UserActivationSerializer(serializers.Serializer):
    token = serializers.CharField()

    def validate_token(self, value):
        try:
            User.objects.get(activation_token=value)
        except User.DoesNotExist:
            raise serializers.ValidationError('Invalid or expired activation token.')
        return value

    def save(self):
        user = User.objects.get(activation_token=self.validated_data['token'])
        user.activate_account()
        return user


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    interests = serializers.PrimaryKeyRelatedField(
        queryset=Interest.objects.all(),
        many=True,
        required=False,
    )
    profile_picture = serializers.URLField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'gender',
            'phone_number',
            'department',
            'year_of_study',
            'bio',
            'profile_picture',
            'interests',
            'user_name',
        ]
        read_only_fields = ['email', 'university_id']

    def update(self, instance, validated_data):
        interests = validated_data.pop('interests', None)
        instance = super().update(instance, validated_data)
        if interests is not None:
            instance.interests.set(interests)
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save(update_fields=['password'])
        return user
