from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase, override_settings
from rest_framework_simplejwt.tokens import AccessToken

from flow.asgi import application

from .models import Room

User = get_user_model()

TEST_CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}


@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS, ALLOWED_HOSTS=['testserver', 'localhost'])
class CallWebsocketTests(TransactionTestCase):
    def setUp(self):
        self.alice = User.objects.create_user(
            email='call-alice@example.com',
            university_id='CALLA001',
            password='pass12345',
            user_name='callalice',
            is_active=True,
        )
        self.bob = User.objects.create_user(
            email='call-bob@example.com',
            university_id='CALLB001',
            password='pass12345',
            user_name='callbob',
            is_active=True,
        )
        self.mallory = User.objects.create_user(
            email='call-mallory@example.com',
            university_id='CALLM001',
            password='pass12345',
            user_name='callmallory',
            is_active=True,
        )
        self.room = Room.objects.create(room_name='11111111-1111-1111-1111-111111111111')
        self.room.participants.set([self.alice, self.bob])

    def test_anonymous_and_non_participants_are_rejected(self):
        async_to_sync(self._anonymous_and_non_participants_are_rejected)()

    async def _anonymous_and_non_participants_are_rejected(self):
        anonymous = WebsocketCommunicator(application, f'/ws/call/{self.room.room_name}/')
        connected, close_code = await anonymous.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 4401)

        token = str(AccessToken.for_user(self.mallory))
        outsider = WebsocketCommunicator(
            application,
            f'/ws/call/{self.room.room_name}/?token={token}',
        )
        connected, close_code = await outsider.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 4403)

    def test_signalling_is_relayed_only_to_the_other_participant(self):
        async_to_sync(self._signalling_is_relayed_only_to_the_other_participant)()

    async def _signalling_is_relayed_only_to_the_other_participant(self):
        alice_token = str(AccessToken.for_user(self.alice))
        bob_token = str(AccessToken.for_user(self.bob))
        alice = WebsocketCommunicator(
            application,
            f'/ws/call/{self.room.room_name}/?token={alice_token}',
        )
        bob = WebsocketCommunicator(
            application,
            f'/ws/call/{self.room.room_name}/?token={bob_token}',
        )

        alice_connected, _ = await alice.connect()
        bob_connected, _ = await bob.connect()
        self.assertTrue(alice_connected)
        self.assertTrue(bob_connected)

        offer = {'type': 'offer', 'offer': {'type': 'offer', 'sdp': 'test-sdp'}}
        await alice.send_json_to(offer)
        relayed = await bob.receive_json_from()

        self.assertEqual(relayed['event_type'], 'offer')
        self.assertEqual(relayed['sender_id'], self.alice.id)
        self.assertEqual(relayed['data'], offer)
        self.assertTrue(await alice.receive_nothing(timeout=0.05))

        await alice.disconnect()
        await bob.disconnect()

    def test_unsupported_signalling_event_returns_a_structured_error(self):
        async_to_sync(self._unsupported_signalling_event_returns_a_structured_error)()

    async def _unsupported_signalling_event_returns_a_structured_error(self):
        token = str(AccessToken.for_user(self.alice))
        communicator = WebsocketCommunicator(
            application,
            f'/ws/call/{self.room.room_name}/?token={token}',
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        await communicator.send_json_to({'type': 'delete-room'})
        response = await communicator.receive_json_from()

        self.assertEqual(response['type'], 'error')
        self.assertIn('Unsupported', response['error'])
        await communicator.disconnect()
