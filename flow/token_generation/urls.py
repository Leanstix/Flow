from django.urls import path
from .views import GenerateAccessTokenView

urlpatterns = [
    path('generate-access-token/', GenerateAccessTokenView.as_view(), name='generate-access-token'),
]