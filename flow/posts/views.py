from django.contrib.auth import get_user_model
from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.models import Notification
from notifications.services import create_notification

from .models import Comment, Like, Post, Report
from .serializers import CommentSerializer, PostSerializer

User = get_user_model()


def post_queryset():
    return Post.objects.select_related("user", "reposted_from", "reposted_from__user").prefetch_related("likes", "comments", "reposts")


def serialize_post(post, request, status_code=status.HTTP_200_OK):
    return Response(PostSerializer(post, context={"request": request}).data, status=status_code)


def with_engagement(queryset):
    return queryset.annotate(
        likes_total=Count("likes", distinct=True),
        comments_total=Count("comments", distinct=True),
        reposts_total=Count("reposts", distinct=True),
    ).annotate(
        engagement=F("likes_total") + F("comments_total") + F("reposts_total")
    )


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "limit"


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def toggle_like(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    like, created = Like.objects.get_or_create(user=request.user, post=post)

    if created:
        liked = True
        create_notification(
            recipient=post.user,
            actor=request.user,
            verb=Notification.Verb.LIKE,
            message=f"{request.user.user_name or request.user.email} liked your post.",
            target_post=post,
        )
    else:
        like.delete()
        liked = False

    return Response({"liked": liked, "likes_count": post.likes.count()}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    serializer = CommentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    comment = serializer.save(post=post, user=request.user)

    create_notification(
        recipient=post.user,
        actor=request.user,
        verb=Notification.Verb.COMMENT,
        message=f"{request.user.user_name or request.user.email} commented on your post.",
        target_post=post,
        target_comment=comment,
    )

    return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reply_to_comment(request, comment_id):
    parent_comment = get_object_or_404(Comment.objects.select_related("post", "user", "post__user"), id=comment_id)
    serializer = CommentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    reply = serializer.save(post=parent_comment.post, parent=parent_comment, user=request.user)

    notified_users = {parent_comment.user_id: parent_comment.user}
    if parent_comment.post.user_id != parent_comment.user_id:
        notified_users[parent_comment.post.user_id] = parent_comment.post.user

    for recipient in notified_users.values():
        create_notification(
            recipient=recipient,
            actor=request.user,
            verb=Notification.Verb.COMMENT_REPLY,
            message=f"{request.user.user_name or request.user.email} replied to a comment.",
            target_post=parent_comment.post,
            target_comment=reply,
        )

    return Response(CommentSerializer(reply).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def repost(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    quote = request.data.get("content", "")
    content = quote.strip() if isinstance(quote, str) and quote.strip() else post.content
    new_post = Post.objects.create(user=request.user, content=content, reposted_from=post)

    create_notification(
        recipient=post.user,
        actor=request.user,
        verb=Notification.Verb.REPOST,
        message=f"{request.user.user_name or request.user.email} reposted your post.",
        target_post=post,
    )

    return serialize_post(new_post, request, status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def report_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    reason = request.data.get("reason", "")
    if not isinstance(reason, str) or not reason.strip():
        return Response({"reason": "A report reason is required."}, status=status.HTTP_400_BAD_REQUEST)
    Report.objects.create(user=request.user, post=post, reason=reason.strip())
    return Response({"message": "Report submitted successfully"}, status=status.HTTP_201_CREATED)


class PostView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_posts = post_queryset().filter(user=request.user).order_by("-created_at")
        serializer = PostSerializer(user_posts, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = PostSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        post = serializer.save(user=request.user)
        return serialize_post(post, request, status.HTTP_201_CREATED)

    def delete(self, request, post_id=None):
        if post_id is None:
            return Response({"error": "post_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        post = get_object_or_404(Post, id=post_id, user=request.user)
        post.delete()
        return Response({"message": "Post deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


class SearchPostsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response({"error": "Query parameter 'q' cannot be empty"}, status=status.HTTP_400_BAD_REQUEST)

        posts = post_queryset().filter(
            Q(content__icontains=query) | Q(user__user_name__icontains=query) | Q(user__email__icontains=query)
        ).exclude(user=request.user).order_by("-created_at")

        paginator = CustomPagination()
        paginated_posts = paginator.paginate_queryset(posts, request, view=self)
        serializer = PostSerializer(paginated_posts, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


class FeedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        friends = User.objects.filter(
            Q(sent_requests__to_user=user, sent_requests__accepted=True) |
            Q(received_requests__from_user=user, received_requests__accepted=True)
        ).distinct()

        posts = with_engagement(post_queryset().filter(Q(user=user) | Q(user__in=friends))).order_by("-engagement", "-created_at")
        serializer = PostSerializer(posts, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class AllFeedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        posts = with_engagement(post_queryset().all()).order_by("-engagement", "-created_at")
        paginator = CustomPagination()
        paginated_posts = paginator.paginate_queryset(posts, request, view=self)
        serializer = PostSerializer(paginated_posts, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


class SearchUserPostsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        query = request.query_params.get("q", "").strip()
        user_posts = post_queryset().filter(user=request.user)
        if query:
            user_posts = user_posts.filter(content__icontains=query)
        user_posts = user_posts.order_by("-created_at")

        paginator = CustomPagination()
        paginated_posts = paginator.paginate_queryset(user_posts, request, view=self)
        serializer = PostSerializer(paginated_posts, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)


class CommentPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "limit"


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_comments(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    comments = post.comments.filter(parent__isnull=True).select_related("user").order_by("-created_at")

    paginator = CommentPagination()
    paginated_comments = paginator.paginate_queryset(comments, request)
    serializer = CommentSerializer(paginated_comments, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_comment_replies(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    replies = comment.replies.select_related("user").order_by("created_at")

    paginator = CommentPagination()
    paginated_replies = paginator.paginate_queryset(replies, request)
    serializer = CommentSerializer(paginated_replies, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id, user=request.user)
    comment.delete()
    return Response({"message": "Comment deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
