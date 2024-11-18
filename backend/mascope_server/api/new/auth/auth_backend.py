"""
Authentication backend configuration for Mascope Server.

This file configures the authentication backends used in the FastAPI Users implementation.
It defines the cookie transport and JWT strategy for mascope web-based interface, 
and bearer transport with database access tokens for the mascope_api jupyter library authentication.
"""

from rich.pretty import pretty_repr
from fastapi import Depends, Request
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import (
    CookieTransport,
    BearerTransport,
    JWTStrategy,
    AuthenticationBackend,
)
from fastapi_users.authentication.strategy.db import (
    AccessTokenDatabase,
    DatabaseStrategy,
)
from mascope_server.db.models import AccessToken, User
from mascope_server.api.new.auth.config import auth_settings
from mascope_server.api.new.auth.util import get_access_token_db
from mascope_server.api.new.users.util import get_user_manager


from mascope_server.runtime import runtime

# Cookie-based authentication for web app (Mascope web-based interface)
cookie_transport = CookieTransport(
    cookie_name=auth_settings.COOKIE_NAME,
    cookie_max_age=auth_settings.COOKIE_MAX_AGE_SECONDS,
    cookie_secure=auth_settings.COOKIE_SECURE,
    cookie_httponly=auth_settings.COOKIE_HTTP_ONLY,
)

# Bearer-based transport for access token authentication in the Jupyter server
access_token_transport = BearerTransport(tokenUrl="/api/auth/access_token/generate")


# JWT strategy for cookie authentication
def get_jwt_strategy() -> JWTStrategy:
    """
    Returns a JWT strategy for handling user authentication via cookies.

    This function configures a JWT (JSON Web Token) strategy, which FastAPI Users uses to handle
    user authentication. The JWT is signed using a secret key and has a defined expiration time.

    :return: A configured JWT strategy for handling authentication.
    :rtype: JWTStrategy
    """
    return JWTStrategy(
        secret=auth_settings.JWT_SECRET_KEY,
        lifetime_seconds=auth_settings.JWT_EXPIRATION_SECONDS,
        token_audience=auth_settings.JWT_AUDIENCE,
        algorithm=auth_settings.JWT_ALGORITHM,
    )


# Database strategy for access token authentication (access token stored in DB)
def get_database_strategy(
    access_token_db: AccessTokenDatabase[AccessToken] = Depends(get_access_token_db),
) -> DatabaseStrategy:
    """
    Returns a DatabaseStrategy for access token authentication.

    This strategy validates access token stored in the database, associating each key with a user ID.
    Tokens expire after the defined lifetime.
    """
    return DatabaseStrategy(
        access_token_db, lifetime_seconds=auth_settings.ACCESS_TOKEN_EXPIRATION_SECONDS
    )


# Cookie-based authentication for the web app
auth_backend_cookie = AuthenticationBackend(
    name="jwt",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)

# Access token-based authentication for Jupyter server/API access
auth_backend_access_token = AuthenticationBackend(
    name="access-token",
    transport=access_token_transport,
    get_strategy=get_database_strategy,
)


# FastAPI Users setup with authentication with both backends
fastapi_users = FastAPIUsers[User, int](
    get_user_manager,
    [auth_backend_cookie, auth_backend_access_token],
)


async def get_enabled_backends(request: Request) -> list[AuthenticationBackend]:
    """
    Determines the appropriate authentication backend to use based on the request's credentials.

    Authentication options:
    - Cookie-based JWT: Used for the Mascope web application. If the `mascope_auth` cookie is present, this backend is selected.
    - Access token-based authentication: Intended for Jupyter server or external API access. Enabled if an 'Authorization' header with a Bearer token is found, but the 'mascope_auth' cookie is absent.

    If neither of these conditions is met:
    - Logs an error and defaults to the cookie-based JWT backend.

    :param request: The incoming HTTP request to inspect for authentication headers or cookies.
    :type request: Request
    :return: A list containing the selected authentication backend.
    :rtype: list[AuthenticationBackend]
    """
    # Debug: Inspecting request details for determining authentication method
    runtime.logger.trace(f"Request scope:\n{pretty_repr(request.scope)}")
    runtime.logger.trace(f"Request headers:\n{pretty_repr(dict(request.headers))}")

    cookie_auth = request.cookies.get("mascope_auth")
    auth_header = request.headers.get("authorization")

    # Access the route function (endpoint handler)
    route_func = request.scope.get("endpoint")

    # Cookie-based JWT for Mascope web app access
    if cookie_auth:
        runtime.logger.debug("Using web application authentication.")
        return [auth_backend_cookie]

    # Access token-based authentication for token access (Jupyter server)
    if auth_header and not cookie_auth:
        # Check if the endpoint allows for token access
        if hasattr(route_func, "token_access") and route_func.token_access:
            runtime.logger.debug(
                "Using Jupyter server or external API access authentication."
            )
            return [auth_backend_access_token]
        else:
            runtime.logger.error("Unauthorized for Jupyter access.")
            return [auth_backend_cookie]

    # No valid authentication credentials found
    runtime.logger.error("Request did not contain a valid authentication credentials.")
    return [auth_backend_cookie]
