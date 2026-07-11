from django.urls import path, re_path

from calls.consumers import CallConsumer, UserCallConsumer
from messaging.consumers import ConversationConsumer
from notifications.consumers import NotificationConsumer


websocket_urlpatterns = [
    re_path(r'ws/call/(?P<room_name>[-\w]+)/$', CallConsumer.as_asgi()),
    path('ws/calls/', UserCallConsumer.as_asgi()),
    path('ws/conversations/<int:conversation_id>/', ConversationConsumer.as_asgi()),
    path('ws/notifications/', NotificationConsumer.as_asgi()),
]
