from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from .serializers import LoginSerializer

class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Generate or retrieve token
            token, created = Token.objects.get_or_create(user=user)
            
            return Response({
                "token": token.key,
                "user_id": user.id,
                "email": user.email
            }, status=status.HTTP_200_OK)
        else:
            print(serializer.errors)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        # Delete the user's token to log them out
        request.user.auth_token.delete()
        return Response({"message": "Successfully logged out."}, status=status.HTTP_200_OK)
