# routing.py
from django.urls import re_path
from calls.consumers import CallConsumer

websocket_urlpatterns = [
    re_path(r'ws/call/(?P<room_name>\w+)/$', CallConsumer.as_asgi()),
]
