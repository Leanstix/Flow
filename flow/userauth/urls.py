from django.urls import path
from django.conf.urls.static import static
from django.conf import settings  # Import settings
from .views import ActivateAccountView, UserRegistrationView, UserActivationView, UserProfileUpdateView, ChangePasswordView

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('activate/', UserActivationView.as_view(), name='activate'),
    path('profile/update/', UserProfileUpdateView.as_view(), name='profile-update'),
    path('activate-account/', ActivateAccountView.as_view(), name='activate-account'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
]

if settings.DEBUG:  # Ensure settings is imported before using it
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
