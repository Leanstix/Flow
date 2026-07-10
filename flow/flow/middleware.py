from urllib.parse import parse_qs

from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError


@database_sync_to_async
def get_user_for_token(token):
    if not token:
        return AnonymousUser()

    try:
        jwt_authentication = JWTAuthentication()
        validated_token = jwt_authentication.get_validated_token(token)
        return jwt_authentication.get_user(validated_token)
    except (InvalidToken, TokenError, Exception):
        return AnonymousUser()


class JwtAuthMiddleware(BaseMiddleware):
    """Authenticate websocket clients with ?token=<jwt-access-token>.

    Session authentication still works through AuthMiddlewareStack. The JWT token
    only overrides the scope user when it is provided and valid.
    """

    async def __call__(self, scope, receive, send):
        close_old_connections()
        query_params = parse_qs(scope.get("query_string", b"").decode())
        token_values = query_params.get("token") or query_params.get("access")
        token = token_values[0] if token_values else None

        if token:
            scope["user"] = await get_user_for_token(token)
        elif "user" not in scope:
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)


def JwtAuthMiddlewareStack(inner):
    return AuthMiddlewareStack(JwtAuthMiddleware(inner))
