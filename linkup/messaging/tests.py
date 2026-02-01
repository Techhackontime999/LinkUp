import asyncio
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Message
from channels.testing import WebsocketCommunicator
from professional_network.asgi import application

User = get_user_model()


class MessagingViewTests(TestCase):
    def setUp(self):
        self.u1 = User.objects.create_user(username='alice', password='pass')
        self.u2 = User.objects.create_user(username='bob', password='pass')

    def test_fetch_history_marks_read(self):
        # bob -> alice (unread)
        m = Message.objects.create(sender=self.u2, recipient=self.u1, content='hello')
        c = Client()
        c.login(username='alice', password='pass')
        url = reverse('messaging:fetch_history', args=[self.u2.username])
        resp = c.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn('messages', data)
        # re-fetch from DB
        m.refresh_from_db()
        self.assertTrue(m.is_read)

    def test_send_message_fallback(self):
        c = Client()
        c.login(username='alice', password='pass')
        url = reverse('messaging:send_message_fallback', args=[self.u2.username])
        resp = c.post(url, {'message': 'hi bob'})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['sender'], 'alice')
        self.assertEqual(data['recipient'], 'bob')
        self.assertTrue(Message.objects.filter(sender=self.u1, recipient=self.u2, content='hi bob').exists())


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class ChatConsumerTests(TestCase):
    async def test_chat_and_notifications(self):
        from asgiref.sync import sync_to_async

        u1 = await sync_to_async(User.objects.create_user)(username='carol', password='pass')
        u2 = await sync_to_async(User.objects.create_user)(username='dave', password='pass')

        client1 = Client()
        await sync_to_async(client1.login)(username='carol', password='pass')
        session1 = client1.cookies['sessionid'].value

        client2 = Client()
        await sync_to_async(client2.login)(username='dave', password='pass')
        session2 = client2.cookies['sessionid'].value

        # Connect both to chat room
        comm1 = WebsocketCommunicator(application, f"/ws/chat/{u2.username}/", headers=[(b'cookie', f'sessionid={session1}'.encode())])
        comm2 = WebsocketCommunicator(application, f"/ws/chat/{u1.username}/", headers=[(b'cookie', f'sessionid={session2}'.encode())])

        connected1, _ = await comm1.connect()
        connected2, _ = await comm2.connect()
        self.assertTrue(connected1 and connected2)

        # Also connect u2 to notifications
        notif_comm = WebsocketCommunicator(application, "/ws/notifications/", headers=[(b'cookie', f'sessionid={session2}'.encode())])
        connected_notif, _ = await notif_comm.connect()
        self.assertTrue(connected_notif)

        # send message from carol -> dave
        await comm1.send_json_to({'message': 'hi dave'})

        # both chat sockets should receive the broadcast
        msg1 = await comm1.receive_json_from()
        msg2 = await comm2.receive_json_from()
        self.assertEqual(msg1['content'], 'hi dave')
        self.assertEqual(msg2['content'], 'hi dave')

        # notifications websocket should receive a notification payload
        notif = await notif_comm.receive_json_from()
        self.assertEqual(notif['content'], 'hi dave')

        # verify DB saved
        # run a sync DB assertion
        exists = await sync_to_async(Message.objects.filter(sender__username='carol', recipient__username='dave', content='hi dave').exists)()
        self.assertTrue(exists)

        await comm1.disconnect()
        await comm2.disconnect()
        await notif_comm.disconnect()

    def test_unread_endpoint(self):
        u1 = User.objects.create_user(username='eve', password='pass')
        u2 = User.objects.create_user(username='frank', password='pass')
        Message.objects.create(sender=u2, recipient=u1, content='msg1')
        Message.objects.create(sender=u2, recipient=u1, content='msg2')
        c = Client()
        c.login(username='eve', password='pass')
        url = reverse('messaging:unread_notifications')
        resp = c.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['count'], 2)
        self.assertTrue(isinstance(data['messages'], list))
    def test_unread_endpoint(self):
        u1 = User.objects.create_user(username='eve', password='pass')
        u2 = User.objects.create_user(username='frank', password='pass')
        Message.objects.create(sender=u2, recipient=u1, content='msg1')
        Message.objects.create(sender=u2, recipient=u1, content='msg2')
        c = Client()
        c.login(username='eve', password='pass')
        url = reverse('messaging:unread_notifications')
        resp = c.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data['count'], 2)
        self.assertTrue(isinstance(data['messages'], list))
