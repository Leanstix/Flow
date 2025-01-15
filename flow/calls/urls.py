# urls.py
from django.urls import path
from .views import create_room, join_room

urlpatterns = [
    path('create-room/', create_room.as_view(), name='create_room'),
    path('join-room/<str:room_name>/', join_room.as_view(), name='join_room'),
]
