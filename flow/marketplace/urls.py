from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AdvertisementViewSet

router = DefaultRouter()
router.register(r'listings', AdvertisementViewSet, basename='marketplace-listing')

urlpatterns = [path('', include(router.urls))]
