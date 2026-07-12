from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions


API_DESCRIPTION = """
Flow is a campus social, messaging, community, marketplace and realtime calling API.

## Authentication

Most operations require a SimpleJWT access token:

```http
Authorization: Bearer <access-token>
```

Access tokens currently expire after 30 minutes. Refresh tokens currently expire after 7 days and can be exchanged at `POST /api/token/generate-access-token/`.

The registration, activation, login and password-reset operations are public. Each protected operation is explicitly marked with the **Bearer** security scheme in this document.

## Content types

- Use `application/json` for normal structured requests.
- Use `multipart/form-data` for profile pictures, marketplace images, post media and message files.
- File-list fields are repeated form fields rather than a JSON array of binary data.
- JSON metadata sent inside multipart forms must be serialized as a JSON string.

## Post media contract

A post may contain up to four images or one video. Images and video cannot be mixed in one post.

Mobile applications must edit and export the final video locally before upload. The backend receives only that final clip and enforces a maximum duration of 180 seconds. Web clients are limited to 90 seconds.

## Message attachment contract

Messages support explicit attachment types: `image`, `video`, `audio`, `document`, `contact`, `location`, and `listing`. Binary attachments use repeated `files` fields. Contact, location and listing attachments use `attachment_payload` metadata.

## Pagination

Paginated responses use this envelope:

```json
{
  "count": 25,
  "next": "https://api.example.com/resource/?page=2",
  "previous": null,
  "results": []
}
```

Some older list operations still return a plain JSON array. Each operation description states the expected shape.

## Realtime WebSocket API

WebSockets are authenticated with a JWT query parameter:

```text
?token=<access-token>
```

Available socket routes:

| Route | Purpose |
|---|---|
| `/ws/conversations/{conversation_id}/` | Message creation, updates, deletion, typing and receipt events. |
| `/ws/notifications/` | Recipient-specific realtime notifications. |
| `/ws/call/{room_name}/` | WebRTC signalling, ICE candidates, media state and network-quality events. |
| `/ws/calls/` | Private incoming-call invitations and lifecycle events for the signed-in user. |

Conversation sockets enforce participant membership. Call-room sockets enforce room participation. Notification and incoming-call sockets are private per-user channels.

## Common status codes

- `200` successful read or update.
- `201` resource created.
- `204` successful deletion with no body.
- `400` validation failure.
- `401` missing or expired credentials.
- `403` authenticated but not permitted.
- `404` resource absent or hidden by ownership/membership isolation.
- `409` invalid call-state transition.
- `413` upload rejected by application or upstream infrastructure.
- `500` unexpected server error.
"""


schema_view = get_schema_view(
    openapi.Info(
        title='Flow API',
        default_version='v1',
        description=API_DESCRIPTION,
        contact=openapi.Contact(name='Flow Engineering', email='leanstixx@gmail.com'),
        license=openapi.License(name='Proprietary - Flow project'),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/marketplace/', include('marketplace.urls')),
    path('api/adds/', include('marketplace.urls')),  # Deprecated backward-compatible alias.
    path('api/groups/', include('communities.urls')),
    path('api/login/', include('login.urls')),
    path('api/', include('messaging.urls')),
    path('api/', include('notifications.urls')),
    path('api/userauth/', include('userauth.urls')),
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('api/posts/', include('posts.urls')),
    path('api/token/', include('token_generation.urls')),
    path('api/requests/', include('requests.urls')),
    path('api/profiles/', include('profiles.urls')),
    path('', lambda request: JsonResponse({'message': 'Welcome to the API of Flow!'})),
    path('api/reset-password/', include('password_reset.urls')),
    path('api/call/', include('calls.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
