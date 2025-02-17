from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Post, Like, Comment, Report
from .serializers import PostSerializer, CommentSerializer
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, F
from django.contrib.auth import get_user_model

User = get_user_model()

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
    def delete(self, request, post_id):
        post = get_object_or_404(Post, id=post_id, user=request.user)
        post.delete()
        return Response({"message": "Post deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
    
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

class FeedView(APIView):
    peclrmission_classes = [IsAuthenticated]

    def get(self, request):
        # Get the authenticated user
        user = request.user

        # Fetch friends of the user (both sent and received accepted requests)
        friends = User.objects.filter(
            Q(sent_requests__to_user=user, sent_requests__accepted=True) |
            Q(received_requests__from_user=user, received_requests__accepted=True)
        ).distinct()

        # Include the user's own posts and the posts from friends
        user_and_friends_posts = Post.objects.filter(
            Q(user=user) | Q(user__in=friends)
        ).annotate(
            engagement=F('likes') + F('comments')  # Calculate engagement as sum of likes and comments
        ).order_by('-engagement', '-created_at')  # Order by engagement first, then by creation date

        # Serialize the posts
        serializer = PostSerializer(user_and_friends_posts, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

class AllFeedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Fetch user's friends (both sent and received accepted requests)
        friends = User.objects.filter(
            Q(sent_requests__to_user=user, sent_requests__accepted=True) |
            Q(received_requests__from_user=user, received_requests__accepted=True)
        ).distinct()

        # Fetch posts from user and friends
        user_and_friends_posts = Post.objects.filter(Q(user=user) | Q(user__in=friends))

        # Fetch all other posts excluding user's posts
        other_posts = Post.objects.exclude(user=user)

        # Combine both sets of posts
        all_posts = user_and_friends_posts | other_posts

        # Annotate with engagement (likes + comments + reposts count)
        all_posts = all_posts.annotate(
            engagement=F("likes") + F("comments") + F("reposts")
        ).order_by("engagement", "created_at")

        # Paginate the results
        paginator = CustomPagination()
        paginated_posts = paginator.paginate_queryset(all_posts, request, view=self)

        # Serialize the posts
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

@api_view(['DELETE'])
def delete_comment(request, comment_id):
    """
    Delete a comment if the authenticated user is the owner.
    """
    comment = get_object_or_404(Comment, id=comment_id, user=request.user)
    comment.delete()
    return Response({"message": "Comment deleted successfully"}, status=status.HTTP_204_NO_CONTENT)