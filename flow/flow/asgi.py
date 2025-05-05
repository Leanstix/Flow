import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from flow.routing import websocket_urlpatterns
from channels.security.websocket import AllowedHostsOriginValidator


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flow.settings')
asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": asgi_app,
    "websocket":  AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                websocket_urlpatterns
            )
        ),
    )
})