from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .serializers import RoomSerializer


def user_call_group(user_id):
    return f'user_calls_{user_id}'


def room_call_group(room_name):
    return f'call_{room_name}'


def serialize_room(room):
    room = (
        room.__class__.objects
        .select_related('created_by', 'conversation')
        .prefetch_related('participants', 'invitations__user', 'invitations__invited_by')
        .get(pk=room.pk)
    )
    return RoomSerializer(room).data


def broadcast_user_call(user_id, event_type, room, extra=None):
    payload = {
        'type': 'call.event',
        'event_type': event_type,
        'call': serialize_room(room),
    }
    if extra:
        payload.update(extra)
    async_to_sync(get_channel_layer().group_send)(user_call_group(user_id), payload)


def broadcast_room_state(room, event_type='call.updated', extra=None):
    payload = {
        'type': 'call.state',
        'event_type': event_type,
        'call': serialize_room(room),
    }
    if extra:
        payload.update(extra)
    async_to_sync(get_channel_layer().group_send)(room_call_group(room.room_name), payload)


def broadcast_call_to_participants(room, event_type, extra=None, exclude_user_id=None):
    participant_ids = room.participants.values_list('id', flat=True)
    for user_id in participant_ids:
        if exclude_user_id and user_id == exclude_user_id:
            continue
        broadcast_user_call(user_id, event_type, room, extra=extra)
