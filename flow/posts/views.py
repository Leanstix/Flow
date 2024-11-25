from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import Post
from .serializers import PostSerializer

class PostView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Fetch posts only created by the authenticated user
        user_posts = Post.objects.filter(user=request.user).order_by("-created_at")
        serializer = PostSerializer(user_posts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        print("POST data:", request.data)  # Log request data
        serializer = PostSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        print("Errors:", serializer.errors)  # Log validation errors
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)