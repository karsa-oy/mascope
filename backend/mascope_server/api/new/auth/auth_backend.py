"""
Authentication backend configuration for Mascope Server.

This file configures the authentication backends used in the FastAPI Users implementation.
It defines the cookie transport, JWT strategy, and API key-based authentication.
"""

from fastapi import Request
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import (
    CookieTransport,
    JWTStrategy,
    AuthenticationBackend,
)
from mascope_server.db.models import User
from mascope_server.api.new.auth.config import auth_settings
from mascope_server.api.new.auth.util import get_user_manager

# Cookie-based authentication for web app (Mascope web-based interface)
cookie_transport = CookieTransport(
    cookie_name=auth_settings.COOKIE_NAME,
    cookie_max_age=auth_settings.COOKIE_MAX_AGE_SECONDS,
    cookie_secure=auth_settings.COOKIE_SECURE,
    cookie_httponly=auth_settings.COOKIE_HTTP_ONLY,
)

# Bearer-based transport for API key authentication in the Jupyter server
# bearer_transport = BearerTransport(tokenUrl="auth/jwt/login") # Second transport for the API key access form the Jupyter server


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


# Database strategy to validate API keys from the database (API key stored in DB)

# # API key (token) stored in the database
# async def get_access_token_db(
#     session: AsyncSession = Depends(get_async_session),
# ) -> SQLAlchemyAccessTokenDatabase:
#     return SQLAlchemyAccessTokenDatabase(session, AccessToken)

# def get_database_strategy(
#     access_token_db: AccessTokenDatabase[AccessToken] = Depends(get_access_token_db),
# ) -> DatabaseStrategy:
#     """Database strategy for API key authentication."""
#     return DatabaseStrategy(access_token_db, lifetime_seconds=3600)


# Cookie-based authentication for the web app
auth_backend_cookie = AuthenticationBackend(
    name="jwt",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)

# # API key-based authentication for Jupyter server/API access
# auth_backend_api_key = AuthenticationBackend(
#     name="api-key",
#     transport=bearer_transport,
#     get_strategy=get_database_strategy,
# )


# FastAPI Users setup with authentication backend(s)
fastapi_users = FastAPIUsers[User, int](
    get_user_manager,
    [
        auth_backend_cookie
        #  , auth_backend_api_key # Enable both backends when API key authentication is added
    ],
)


async def get_enabled_backends(request: Request):
    """
    Dynamically enable the correct authentication backend based on the request.
    - If the request comes from the Jupyter API, use the API key backend.
    - Otherwise, default to cookie-based JWT for the web app.
    """
    # # Using a custom header to distinguish between API and web requests
    # if "X-Mascope-Api" in request.headers:
    #     return [auth_backend_api_key]
    # else:
    #     return [auth_backend_cookie]
    return [auth_backend_cookie]
