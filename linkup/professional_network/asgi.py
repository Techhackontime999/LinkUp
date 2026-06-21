import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from whitenoise import WhiteNoise

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'professional_network.settings')

django_asgi_app = get_asgi_application()
django_asgi_app = WhiteNoise(django_asgi_app)

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(__import__('messaging.routing', fromlist=['websocket_urlpatterns']).websocket_urlpatterns)
    ),
})
