# urls.py
from django.urls import path
from .views import create_room, join_room

urlpatterns = [
    path('create-room/', create_room, name='create_room'),
    path('join-room/<str:room_name>/', join_room, name='join_room'),
]
