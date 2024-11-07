from django.urls import path
from .views import UserRegistrationView, UserActivationView, UserProfileUpdateView

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('activate/', UserActivationView.as_view(), name='activate'),
    path('profile/update/', UserProfileUpdateView.as_view(), name='profile-update'),
]
