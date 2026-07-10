from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CommunityPostViewSet, CommunityResourceViewSet, CommunityViewSet

router = DefaultRouter()
router.register(r'posts', CommunityPostViewSet, basename='community-post')
router.register(r'resources', CommunityResourceViewSet, basename='community-resource')
router.register(r'', CommunityViewSet, basename='community')

urlpatterns = [path('', include(router.urls))]
