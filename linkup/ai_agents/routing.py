"""
WebSocket URL routing for AI agent connections.
Handles real-time communication for AI agents.
"""

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Agent WebSocket - connects AI agents for real-time messaging
    # Pattern: ws/agents/
    # Authentication via JWT token in query parameters or headers
    re_path(r'ws/agents/$'$', consumers.AgentConsumer.as_asgi()),
]
