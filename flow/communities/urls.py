from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CommunityPostViewSet, CommunityResourceViewSet, CommunityViewSet

router = DefaultRouter()
router.register(r'groups', CommunityViewSet, basename='community')
router.register(r'posts', CommunityPostViewSet, basename='community-post')
router.register(r'resources', CommunityResourceViewSet, basename='community-resource')

urlpatterns = [path('', include(router.urls))]
