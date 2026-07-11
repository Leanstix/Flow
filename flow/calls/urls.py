from django.urls import path

from .views import (
    AcceptCallView,
    CallDetailView,
    CreateRoomView,
    DirectCallView,
    IncomingCallsView,
    InviteParticipantsView,
    JoinRoomView,
    LeaveCallView,
    RejectCallView,
)

urlpatterns = [
    path('create-room/', CreateRoomView.as_view(), name='create_room'),
    path('join-room/<str:room_name>/', JoinRoomView.as_view(), name='join_room'),
    path('direct/', DirectCallView.as_view(), name='direct_call'),
    path('incoming/', IncomingCallsView.as_view(), name='incoming_calls'),
    path('<str:room_name>/', CallDetailView.as_view(), name='call_detail'),
    path('<str:room_name>/accept/', AcceptCallView.as_view(), name='accept_call'),
    path('<str:room_name>/reject/', RejectCallView.as_view(), name='reject_call'),
    path('<str:room_name>/invite/', InviteParticipantsView.as_view(), name='invite_call_participants'),
    path('<str:room_name>/leave/', LeaveCallView.as_view(), name='leave_call'),
]
