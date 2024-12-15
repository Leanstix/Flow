from django.urls import path
from .views import UserProfileView

urlpatterns = [
    path('profile/<int:user_id>/', UserProfileView.as_view(), name='user-profile'),
]
