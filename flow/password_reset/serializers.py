from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils.encoding import smart_str, smart_bytes, DjangoUnicodeDecodeError
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import PasswordResetTokenGenerator

User = get_user_model()

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email does not exist.")
        return value


class PasswordResetVerifySerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()

    def validate(self, data):
        try:
            uid = smart_str(urlsafe_base64_decode(data['uid']))
            user = User.objects.get(id=uid)
            token_generator = PasswordResetTokenGenerator()
            if not token_generator.check_token(user, data['token']):
                raise serializers.ValidationError("Invalid or expired token.")
        except (DjangoUnicodeDecodeError, User.DoesNotExist):
            raise serializers.ValidationError("Invalid token or user ID.")
        return data


class PasswordResetCompleteSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate(self, data):
        try:
            uid = smart_str(urlsafe_base64_decode(data['uid']))
            user = User.objects.get(id=uid)
            token_generator = PasswordResetTokenGenerator()
            if not token_generator.check_token(user, data['token']):
                raise serializers.ValidationError("Invalid or expired token.")
            data['user'] = user
        except (DjangoUnicodeDecodeError, User.DoesNotExist):
            raise serializers.ValidationError("Invalid token or user ID.")
        return data

    def save(self):
        user = self.validated_data['user']
        user.set_password(self.validated_data['password'])
        user.save()
        return user
