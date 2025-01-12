from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.urls import path
from django.contrib import admin
from django.urls import include
from django.conf.urls.static import static
from django.conf import settings
from django.http import JsonResponse

schema_view = get_schema_view(
    openapi.Info(
        title="Your API",
        default_version="v1",
        description="API documentation",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@example.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/adds/', include('marketplace.urls')),
    path('api/login/', include('login.urls')),
    path('api/', include('messaging.urls')),
    path('api/userauth/', include('userauth.urls')),  # Ensure 'userauth.urls' exists and is correct
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('api/posts/', include('posts.urls')),
    path('api/token/', include('token_generation.urls')),
    path('api/requests/', include('requests.urls')),
    path('api/profiles/', include('profiles.urls')),
    path('', lambda request: JsonResponse({'message': 'Welcome to the API of Flow!'})),
    path('api/reset-password/', include('password_reset.urls')),
    path('api/call/', include('calls.urls'))
]

if settings.DEBUG:  # Serve media files only in development
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)