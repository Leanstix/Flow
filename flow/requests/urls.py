from django.urls import path
from .views import SearchUserView, FriendRequestView, ViewFriendsView

urlpatterns = [
    path("search/", SearchUserView.as_view(), name="search-users"),
    path("friends/", ViewFriendsView.as_view(), name="view_friends"),
    path("friend-requests/", FriendRequestView.as_view(), name="friend-requests"),
    path("friend-requests/<int:pk>/", FriendRequestView.as_view(), name="accept-friend-request"),
]
