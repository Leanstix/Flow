from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Post, Like, Comment, Report
from .serializers import PostSerializer, CommentSerializer
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.pagination import PageNumberPagination

# Get or Create Like (Toggle Like)
@api_view(['POST'])
def toggle_like(request, post_id):
    user = request.user
    post = get_object_or_404(Post, id=post_id)

    like, created = Like.objects.get_or_create(user=user, post=post)
    if not created:
        like.delete()  # Unlike if already liked
        liked = False
    else:
        liked = True

    return Response({'liked': liked, 'likes_count': post.likes_count})

# Add Comment to a Post
@api_view(['POST'])
def add_comment(request, post_id):
    user = request.user
    post = get_object_or_404(Post, id=post_id)
    serializer = CommentSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(post=post, user=user)
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)

# Repost a Post (Create a new post from an existing one)
@api_view(['POST'])
def repost(request, post_id):
    user = request.user
    post = get_object_or_404(Post, id=post_id)
    new_post = Post.objects.create(user=user, content=post.content, reposted_from=post)
    return Response(PostSerializer(new_post).data, status=201)

# Report a Post
@api_view(['POST'])
def report_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    reason = request.data.get('reason', '')
    report = Report.objects.create(user=request.user, post=post, reason=reason)
    return Response({'message': 'Report submitted successfully'}, status=201)

# Get all Posts by the authenticated user
class PostView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_posts = Post.objects.filter(user=request.user).order_by("-created_at")
        serializer = PostSerializer(user_posts, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = PostSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "limit"

class SearchPostsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response({"error": "Query parameter 'q' cannot be empty"}, status=status.HTTP_400_BAD_REQUEST)

        # Filter posts based on content or username, excluding the current user's posts
        posts = Post.objects.filter(
            Q(content__icontains=query) | Q(user__username__icontains=query)
        ).exclude(user=request.user).order_by("-created_at")

        paginator = CustomPagination()
        paginated_posts = paginator.paginate_queryset(posts, request, view=self)
        serializer = PostSerializer(paginated_posts, many=True)

        return paginator.get_paginated_response(serializer.data)
    
class SearchUserPostsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        query = request.query_params.get("q", "").strip()
        
        # If query is empty, fetch all posts
        user_posts = Post.objects.filter(user=request.user)
        if query:
            user_posts = user_posts.filter(content__icontains=query)
        
        user_posts = user_posts.order_by("-created_at")  # Order by newest first

        # Paginate the results
        paginator = PageNumberPagination()
        paginated_posts = paginator.paginate_queryset(user_posts, request, view=self)

        serializer = PostSerializer(paginated_posts, many=True)

        return paginator.get_paginated_response(serializer.data)



class CommentPagination(PageNumberPagination):
    page_size = 10  # Default number of comments per page
    page_size_query_param = "limit"  # 

@api_view(['GET'])
def get_comments(request, post_id):
    """
    Fetch comments for a specific post.
    Supports pagination with 'limit' and 'page' query parameters.
    """
    post = get_object_or_404(Post, id=post_id)  # Ensure the post exists
    comments = post.comments.all().order_by("-created_at")  # Fetch comments ordered by newest first

    # Paginate the results
    paginator = CommentPagination()
    paginated_comments = paginator.paginate_queryset(comments, request)
    serializer = CommentSerializer(paginated_comments, many=True)
    
    return paginator.get_paginated_response(serializer.data)