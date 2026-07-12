from django.urls import path

from .views import (
    AllFeedView,
    FeedView,
    HashtagPostsView,
    HashtagSearchView,
    PostView,
    SearchPostsView,
    SearchUserPostsView,
    add_comment,
    delete_comment,
    get_comment_replies,
    get_comments,
    reply_to_comment,
    report_post,
    repost,
    toggle_like,
)

urlpatterns = [
    path('', PostView.as_view(), name='posts'),
    path('<int:post_id>/comments/', get_comments, name='get_comments'),
    path('<int:post_id>/like/', toggle_like, name='toggle_like'),
    path('<int:post_id>/comment/', add_comment, name='add_comment'),
    path('<int:post_id>/repost/', repost, name='repost'),
    path('<int:post_id>/delete/', PostView.as_view(), name='delete_post'),
    path('<int:post_id>/report/', report_post, name='report_post'),
    path('comments/<int:comment_id>/reply/', reply_to_comment, name='reply_to_comment'),
    path('comments/<int:comment_id>/replies/', get_comment_replies, name='get_comment_replies'),
    path('comments/<int:comment_id>/delete/', delete_comment, name='delete_comment'),
    path('hashtags/', HashtagSearchView.as_view(), name='hashtag_search'),
    path('hashtags/<str:tag>/', HashtagPostsView.as_view(), name='hashtag_posts'),
    path('search/by-user/', SearchUserPostsView.as_view(), name='search_user_posts'),
    path('search/not-by-user/', SearchPostsView.as_view(), name='search_posts'),
    path('feed/', FeedView.as_view(), name='feed'),
    path('all-feed/', AllFeedView.as_view(), name='all_feed'),
]
