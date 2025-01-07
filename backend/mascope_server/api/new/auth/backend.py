"""
Authentication backend configuration for Mascope Server.

This file configures the authentication backends used in the FastAPI Users implementation.
It defines the cookie transport and JWT strategy for mascope web-based interface, 
and bearer transport with database access tokens for the mascope_api jupyter library authentication.
"""

from rich.pretty import pretty_repr
from fastapi import Request
from fastapi_users.authentication import (
    AuthenticationBackend,
)
from mascope_server.api.new.auth.transports import (
    access_token_transport,
    cookie_transport,
)
from mascope_server.api.new.auth.strategies import (
    get_database_strategy,
    get_jwt_strategy,
)
from mascope_server.runtime import runtime


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
