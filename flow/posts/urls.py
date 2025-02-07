from django.urls import path
from .views import PostView, SearchPostsView, SearchUserPostsView,AllFeedView ,toggle_like, add_comment, get_comments, repost, report_post, FeedView

urlpatterns = [
    path("", PostView.as_view(), name="posts"),
    path('<int:post_id>/comments/', get_comments, name='get_comments'),
    path("<int:post_id>/like/", toggle_like, name="toggle_like"),
    path("<int:post_id>/comment/", add_comment, name="add_comment"),
    path("<int:post_id>/repost/", repost, name="repost"),
    path("<int:post_id>/report/", report_post, name="report_post"),
    path("search/by-user/", SearchUserPostsView.as_view(), name="search_user_posts"),
    path("search/not-by-user/", SearchPostsView.as_view(), name="search_posts"),
    path("feed/", FeedView.as_view(), name="feed"),  # Added endpoint for the feed
    pathe("all-feed/", AllFeedView.as_view(), name="all_feed"),  # Added endpoint for the all feed 
]
