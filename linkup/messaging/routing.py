from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # connect to a chat with another user by username
    re_path(r'ws/chat/(?P<username>[^/]+)/$', consumers.ChatConsumer.as_asgi()),
    # connect to a user-level notifications channel
    re_path(r'ws/notifications/$', consumers.NotificationsConsumer.as_asgi()),
]