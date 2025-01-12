from django.urls import path
from .consumers import CallConsumer

websocket_urlpatterns = [
    path('ws/call/<str:room_name>/', CallConsumer.as_asgi()),
]