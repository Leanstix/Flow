from django.urls import path
from .views import PostView, SearchPostsView, SearchUserPostsView, toggle_like, add_comment, get_comments, repost, report_post

urlpatterns = [
    path("posts/", PostView.as_view(), name="posts"),
    path('posts/<int:post_id>/comments/', get_comments, name='get_comments'),
    path("posts/<int:post_id>/like/", toggle_like, name="toggle_like"),
    path("posts/<int:post_id>/comment/", add_comment, name="add_comment"),
    path("posts/<int:post_id>/repost/", repost, name="repost"),
    path("posts/<int:post_id>/report/", report_post, name="report_post"),
    path("posts/search/by-user/", SearchUserPostsView.as_view(), name="search_user_posts"),
    path("posts/search/not-by-user/", SearchPostsView.as_view(), name="search_posts"),
]