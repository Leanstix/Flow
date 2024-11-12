from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework.exceptions import AuthenticationFailed

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        if email and password:
            # Authenticate user with provided credentials
            user = authenticate(username=email, password=password)
            if user:
                # Check if the user is active
                if not user.is_active:
                    raise AuthenticationFailed("This account is inactive.")
                return {'user': user}  # Return the authenticated user object
            else:
                raise AuthenticationFailed("Invalid email or password.")
        else:
            raise serializers.ValidationError("Must include 'email' and 'password'")
