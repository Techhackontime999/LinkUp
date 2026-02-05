"""
Integration test for core real-time messaging features.
Validates that all implemented features work together correctly.
"""

import pytest
import asyncio
import json
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from django.test import TransactionTestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from messaging.consumers import ChatConsumer
from messaging.models import Message, UserStatus, TypingStatus
from messaging.message_status_manager import message_status_manager
from messaging.typing_manager import typing_manager
from messaging.presence_manager import presence_manager

User = get_user_model()


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}})
class CoreFeaturesIntegrationTest(TransactionTestCase):
    """Integration test for all core real-time messaging features."""
    
    def setUp(self):
        """Set up test users."""
        self.user1 = User.objects.create_user(
            username='in