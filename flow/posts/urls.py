from django.urls import path
from .views import PostView, toggle_like, add_comment, get_comments, repost, report_post

urlpatterns = [
    path("posts/", PostView.as_view(), name="posts"),
    path('posts/<int:post_id>/comments/', get_comments, name='get_comments'),
    path("posts/<int:post_id>/like/", toggle_like, name="toggle_like"),
    path("posts/<int:post_id>/comment/", add_comment, name="add_comment"),
    path("posts/<int:post_id>/repost/", repost, name="repost"),
    path("posts/<int:post_id>/report/", report_post, name="report_post"),
]
