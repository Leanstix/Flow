from django.urls import path
from .views import PasswordResetRequestView, PasswordResetVerifyView, PasswordResetCompleteView

urlpatterns = [
    path('password-reset-request/', PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset-verify/', PasswordResetVerifyView.as_view(), name='password-reset-verify'),
    path('password-reset-complete/', PasswordResetCompleteView.as_view(), name='password-reset-complete'),
]
