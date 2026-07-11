from django.contrib.auth import get_user_model
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from messaging.models import Conversation

from .models import CallInvitation, Room
from .serializers import RoomSerializer
from .services import (
    broadcast_call_to_participants,
    broadcast_room_state,
    broadcast_user_call,
)

User = get_user_model()
MAX_CALL_PARTICIPANTS = 8


def room_queryset():
    return Room.objects.select_related('created_by', 'conversation').prefetch_related(
        'participants',
        'invitations__user',
        'invitations__invited_by',
    )


def room_for_user(room_name, user):
    return get_object_or_404(room_queryset(), room_name=room_name, participants=user)


def validate_call_type(value):
    return value if value in {'audio', 'video'} else None


class CreateRoomView(APIView):
    """Backward-compatible open room creation."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        call_type = validate_call_type(request.data.get('call_type', 'video'))
        if not call_type:
            return Response({'call_type': 'Use audio or video.'}, status=status.HTTP_400_BAD_REQUEST)

        room = Room.objects.create(
            created_by=request.user,
            call_type=call_type,
            status='active',
            started_at=timezone.now(),
        )
        room.participants.add(request.user)
        return Response(RoomSerializer(room_queryset().get(pk=room.pk)).data, status=status.HTTP_201_CREATED)


class JoinRoomView(APIView):
    """Join an open room by code or accept an existing invitation."""

    permission_classes = [IsAuthenticated]

    def post(self, request, room_name):
        room = get_object_or_404(room_queryset(), room_name=room_name)
        if room.status in {'ended', 'rejected', 'missed'}:
            return Response({'detail': 'This call has ended.'}, status=status.HTTP_409_CONFLICT)

        already_participant = room.participants.filter(pk=request.user.pk).exists()
        invitation = room.invitations.filter(user=request.user).first()
        if room.invitations.exists() and not already_participant and not invitation:
            return Response({'detail': 'You have not been invited to this call.'}, status=status.HTTP_403_FORBIDDEN)

        room.participants.add(request.user)
        if invitation:
            invitation.status = 'accepted'
            invitation.responded_at = timezone.now()
            invitation.save(update_fields=['status', 'responded_at'])
        if room.status == 'ringing':
            room.status = 'active'
            room.started_at = room.started_at or timezone.now()
            room.save(update_fields=['status', 'started_at'])

        broadcast_call_to_participants(room, 'call.updated')
        broadcast_room_state(room, 'call.updated')
        return Response(RoomSerializer(room_queryset().get(pk=room.pk)).data)


class DirectCallView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        call_type = validate_call_type(request.data.get('call_type', 'audio'))
        if not call_type:
            return Response({'call_type': 'Use audio or video.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            recipient_id = int(request.data.get('recipient_id'))
        except (TypeError, ValueError):
            return Response({'recipient_id': 'A valid recipient is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if recipient_id == request.user.id:
            return Response({'recipient_id': 'You cannot call yourself.'}, status=status.HTTP_400_BAD_REQUEST)

        recipient = get_object_or_404(User.objects.filter(is_active=True), pk=recipient_id)
        conversation = None
        conversation_id = request.data.get('conversation_id')
        if conversation_id not in (None, ''):
            conversation = get_object_or_404(Conversation, pk=conversation_id, participants=request.user)
            if not conversation.participants.filter(pk=recipient.pk).exists():
                return Response({'conversation_id': 'The recipient is not part of this conversation.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            room = Room.objects.create(
                created_by=request.user,
                conversation=conversation,
                call_type=call_type,
                status='ringing',
            )
            room.participants.add(request.user, recipient)
            CallInvitation.objects.create(
                room=room,
                user=request.user,
                invited_by=request.user,
                status='accepted',
                responded_at=timezone.now(),
            )
            CallInvitation.objects.create(
                room=room,
                user=recipient,
                invited_by=request.user,
                status='ringing',
            )

        broadcast_user_call(recipient.id, 'call.incoming', room)
        return Response(RoomSerializer(room_queryset().get(pk=room.pk)).data, status=status.HTTP_201_CREATED)


class IncomingCallsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        rooms = room_queryset().filter(
            invitations__user=request.user,
            invitations__status='ringing',
            status__in=['ringing', 'active'],
        ).distinct()
        return Response(RoomSerializer(rooms, many=True).data)


class CallDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, room_name):
        room = room_for_user(room_name, request.user)
        return Response(RoomSerializer(room).data)


class AcceptCallView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, room_name):
        room = room_for_user(room_name, request.user)
        if room.status in {'ended', 'rejected', 'missed'}:
            return Response({'detail': 'This call is no longer available.'}, status=status.HTTP_409_CONFLICT)

        invitation = get_object_or_404(CallInvitation, room=room, user=request.user)
        invitation.status = 'accepted'
        invitation.responded_at = timezone.now()
        invitation.save(update_fields=['status', 'responded_at'])
        room.status = 'active'
        room.started_at = room.started_at or timezone.now()
        room.save(update_fields=['status', 'started_at'])

        broadcast_call_to_participants(room, 'call.accepted', extra={'accepted_by': request.user.id})
        broadcast_room_state(room, 'call.accepted', extra={'accepted_by': request.user.id})
        return Response(RoomSerializer(room_queryset().get(pk=room.pk)).data)


class RejectCallView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, room_name):
        room = room_for_user(room_name, request.user)
        invitation = get_object_or_404(CallInvitation, room=room, user=request.user)
        invitation.status = 'rejected'
        invitation.responded_at = timezone.now()
        invitation.save(update_fields=['status', 'responded_at'])

        remaining = room.invitations.filter(status__in=['ringing', 'accepted']).exclude(user=room.created_by).exists()
        if not remaining:
            room.status = 'rejected'
            room.ended_at = timezone.now()
            room.save(update_fields=['status', 'ended_at'])

        if room.created_by_id:
            broadcast_user_call(room.created_by_id, 'call.rejected', room, extra={'rejected_by': request.user.id})
        broadcast_room_state(room, 'call.rejected', extra={'rejected_by': request.user.id})
        return Response(RoomSerializer(room_queryset().get(pk=room.pk)).data)


class InviteParticipantsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, room_name):
        room = room_for_user(room_name, request.user)
        if room.status not in {'ringing', 'active'}:
            return Response({'detail': 'Participants cannot be added to an ended call.'}, status=status.HTTP_409_CONFLICT)

        caller_invitation = room.invitations.filter(user=request.user, status='accepted').first()
        if room.invitations.exists() and not caller_invitation:
            return Response({'detail': 'Only active call participants can add people.'}, status=status.HTTP_403_FORBIDDEN)

        raw_ids = request.data.get('user_ids', [])
        if not isinstance(raw_ids, list):
            return Response({'user_ids': 'Provide a list of user IDs.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user_ids = list(dict.fromkeys(int(value) for value in raw_ids))
        except (TypeError, ValueError):
            return Response({'user_ids': 'Every user ID must be valid.'}, status=status.HTTP_400_BAD_REQUEST)

        current_count = room.participants.count()
        available_slots = MAX_CALL_PARTICIPANTS - current_count
        existing_ids = set(room.participants.values_list('id', flat=True))
        new_ids = [user_id for user_id in user_ids if user_id not in existing_ids and user_id != request.user.id]
        if len(new_ids) > available_slots:
            return Response({'user_ids': f'Calls support up to {MAX_CALL_PARTICIPANTS} participants.'}, status=status.HTTP_400_BAD_REQUEST)

        users = list(User.objects.filter(id__in=new_ids, is_active=True))
        if len(users) != len(new_ids):
            return Response({'user_ids': 'One or more users are unavailable.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            for user in users:
                room.participants.add(user)
                invitation, _ = CallInvitation.objects.update_or_create(
                    room=room,
                    user=user,
                    defaults={
                        'invited_by': request.user,
                        'status': 'ringing',
                        'responded_at': None,
                    },
                )
                broadcast_user_call(user.id, 'call.incoming', room, extra={'invitation_id': invitation.id})

        broadcast_call_to_participants(room, 'call.updated', exclude_user_id=None)
        broadcast_room_state(room, 'call.updated')
        return Response(RoomSerializer(room_queryset().get(pk=room.pk)).data)


class LeaveCallView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, room_name):
        room = room_for_user(room_name, request.user)
        invitation = room.invitations.filter(user=request.user).first()
        if invitation:
            invitation.status = 'left'
            invitation.responded_at = timezone.now()
            invitation.save(update_fields=['status', 'responded_at'])

        room.participants.remove(request.user)
        active_others = room.invitations.filter(status='accepted').exclude(user=request.user).count()
        if request.user.id == room.created_by_id or active_others <= 1:
            room.status = 'ended'
            room.ended_at = timezone.now()
            room.save(update_fields=['status', 'ended_at'])
            broadcast_call_to_participants(room, 'call.ended', extra={'ended_by': request.user.id})
            broadcast_room_state(room, 'call.ended', extra={'ended_by': request.user.id})
        else:
            broadcast_call_to_participants(room, 'call.participant_left', extra={'user_id': request.user.id})
            broadcast_room_state(room, 'call.participant_left', extra={'user_id': request.user.id})

        return Response({'detail': 'You left the call.', 'status': room.status})
