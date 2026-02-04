"""
WebSocket URL routing for messaging application.
Handles real-time chat and notification connections.
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Chat WebSocket - connects users for private messaging
    # Pattern: ws/chat/<username>/
    re_path(r'ws/chat/(?P<username>[^/]+)/$', consumers.ChatConsumer.as_asgi()),
    
    # Notifications WebSocket - handles real-time notifications
    # Pattern: ws/notifications/
    re_path(r'ws/notifications/$', consumers.NotificationsConsumer.as_asgi()),
]