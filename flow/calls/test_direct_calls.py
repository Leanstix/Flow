from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase, override_settings
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from flow.asgi import application
from messaging.models import Conversation

from .models import CallInvitation, Room

User = get_user_model()

TEST_CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}


class DirectCallApiTests(APITestCase):
    def setUp(self):
        self.alice = User.objects.create_user(
            email='direct-alice@example.com', university_id='DIRA001', password='pass12345', user_name='alice', is_active=True,
        )
        self.bob = User.objects.create_user(
            email='direct-bob@example.com', university_id='DIRB001', password='pass12345', user_name='bob', is_active=True,
        )
        self.charlie = User.objects.create_user(
            email='direct-charlie@example.com', university_id='DIRC001', password='pass12345', user_name='charlie', is_active=True,
        )
        self.mallory = User.objects.create_user(
            email='direct-mallory@example.com', university_id='DIRM001', password='pass12345', user_name='mallory', is_active=True,
        )
        self.conversation = Conversation.objects.create()
        self.conversation.participants.set([self.alice, self.bob])

    def test_direct_call_accept_and_add_participant(self):
        self.client.force_authenticate(self.alice)
        response = self.client.post('/api/call/direct/', {
            'recipient_id': self.bob.id,
            'conversation_id': self.conversation.id,
            'call_type': 'video',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        room = Room.objects.get(room_name=response.data['room_name'])
        self.assertEqual(room.status, 'ringing')
        self.assertEqual(set(room.participants.values_list('id', flat=True)), {self.alice.id, self.bob.id})
        self.assertEqual(room.invitations.get(user=self.alice).status, 'accepted')
        self.assertEqual(room.invitations.get(user=self.bob).status, 'ringing')

        self.client.force_authenticate(self.bob)
        accepted = self.client.post(f'/api/call/{room.room_name}/accept/')
        self.assertEqual(accepted.status_code, 200)
        room.refresh_from_db()
        self.assertEqual(room.status, 'active')
        self.assertIsNotNone(room.started_at)

        invited = self.client.post(f'/api/call/{room.room_name}/invite/', {'user_ids': [self.charlie.id]}, format='json')
        self.assertEqual(invited.status_code, 200)
        self.assertTrue(room.participants.filter(pk=self.charlie.pk).exists())
        self.assertEqual(CallInvitation.objects.get(room=room, user=self.charlie).status, 'ringing')

    def test_direct_call_validates_conversation_and_permissions(self):
        self.client.force_authenticate(self.alice)
        invalid = self.client.post('/api/call/direct/', {
            'recipient_id': self.charlie.id,
            'conversation_id': self.conversation.id,
            'call_type': 'audio',
        }, format='json')
        self.assertEqual(invalid.status_code, 400)

        valid = self.client.post('/api/call/direct/', {
            'recipient_id': self.bob.id,
            'conversation_id': self.conversation.id,
            'call_type': 'audio',
        }, format='json')
        room_name = valid.data['room_name']

        self.client.force_authenticate(self.mallory)
        self.assertEqual(self.client.get(f'/api/call/{room_name}/').status_code, 404)
        self.assertEqual(self.client.post(f'/api/call/{room_name}/invite/', {'user_ids': [self.charlie.id]}, format='json').status_code, 404)

    def test_rejecting_a_direct_call_closes_it(self):
        self.client.force_authenticate(self.alice)
        response = self.client.post('/api/call/direct/', {'recipient_id': self.bob.id, 'call_type': 'audio'}, format='json')
        room = Room.objects.get(room_name=response.data['room_name'])

        self.client.force_authenticate(self.bob)
        rejected = self.client.post(f'/api/call/{room.room_name}/reject/')
        self.assertEqual(rejected.status_code, 200)
        room.refresh_from_db()
        self.assertEqual(room.status, 'rejected')
        self.assertIsNotNone(room.ended_at)


@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS, ALLOWED_HOSTS=['testserver', 'localhost'])
class MultipartyCallWebsocketTests(TransactionTestCase):
    def setUp(self):
        self.alice = User.objects.create_user(email='mesh-a@example.com', university_id='MESHA001', password='pass12345', user_name='alice', is_active=True)
        self.bob = User.objects.create_user(email='mesh-b@example.com', university_id='MESHB001', password='pass12345', user_name='bob', is_active=True)
        self.charlie = User.objects.create_user(email='mesh-c@example.com', university_id='MESHC001', password='pass12345', user_name='charlie', is_active=True)
        self.room = Room.objects.create(room_name='mesh-room', created_by=self.alice, status='active', call_type='video')
        self.room.participants.set([self.alice, self.bob, self.charlie])

    def test_targeted_offer_only_reaches_selected_participant(self):
        async_to_sync(self._targeted_offer_only_reaches_selected_participant)()

    async def _targeted_offer_only_reaches_selected_participant(self):
        clients = []
        for user in [self.alice, self.bob, self.charlie]:
            token = str(AccessToken.for_user(user))
            client = WebsocketCommunicator(application, f'/ws/call/{self.room.room_name}/?token={token}')
            connected, _ = await client.connect()
            self.assertTrue(connected)
            clients.append(client)

        alice, bob, charlie = clients
        await alice.send_json_to({
            'type': 'offer',
            'target_id': self.bob.id,
            'sdp': {'type': 'offer', 'sdp': 'mesh-sdp'},
        })
        received = await bob.receive_json_from()
        self.assertEqual(received['event_type'], 'offer')
        self.assertEqual(received['sender_id'], self.alice.id)
        self.assertEqual(received['target_id'], self.bob.id)
        self.assertTrue(await charlie.receive_nothing(timeout=0.05))
        self.assertTrue(await alice.receive_nothing(timeout=0.05))

        for client in clients:
            await client.disconnect()
