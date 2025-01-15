# urls.py
from django.urls import path
from .views import CreateRoomView, JoinRoomView

urlpatterns = [
    path('create-room/', CreateRoomView.as_view(), name='create_room'),
    path('join-room/<str:room_name>/', JoinRoomView.as_view(), name='join_room'),
]
