"""
WebSocket URL routing for messaging application.
Handles real-time chat and notification connections.
"""

from django.urls import re_path
from . import consumers
from .routing_validator import RoutingValidator

# Initialize routing validator for startup validation
routing_validator = RoutingValidator()

websocket_urlpatterns = [
    # Chat WebSocket - connects users for private messaging
    # Pattern: ws/chat/<username>/
    re_path(r'ws/chat/(?P<username>[^/]+)/$', consumers.ChatConsumer.as_asgi()),
    
    # Notifications WebSocket - handles real-time notifications
    # Pattern: ws/notifications/
    re_path(r'ws/notifications/$', consumers.NotificationsConsumer.as_asgi()),
]

# Validate routing patterns at startup
def validate_routing_at_startup():
    """Validate WebSocket routing patterns at application startup"""
    try:
        validation_result = routing_validator.validate_routing_patterns([
            (pattern.pattern.pattern, pattern.callback)
            for pattern in websocket_urlpatterns
        ])

        if not validation_result['is_valid']:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"WebSocket routing validation failed: {validation_result['errors']}")

            # In development, raise an error to catch issues early
            import os
            if os.environ.get('DEBUG', 'False').lower() == 'true':
                from django.core.exceptions import ImproperlyConfigured
                raise ImproperlyConfigured(
                    f"Invalid WebSocket routing patterns: {'; '.join(validation_result['errors'])}"
                )
        else:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"WebSocket routing validation successful: {validation_result['valid_patterns']} patterns validated")

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Routing validation error: {e}")

# Perform validation when module is imported
validate_routing_at_startup()