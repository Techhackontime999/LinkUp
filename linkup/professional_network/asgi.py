"""
ASGI config for professional_network project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'professional_network.settings')

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    # WebSocket handler will be added later via routing and consumers
    "websocket": AuthMiddlewareStack(
        # WebSocket URL routing for apps
        URLRouter(__import__('messaging.routing', fromlist=['websocket_urlpatterns']).websocket_urlpatterns)
    ),
})
