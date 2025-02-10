"""
Authentication backend configuration for Mascope Server.

This file configures the authentication backends used in the FastAPI Users implementation.
It defines the cookie transport and JWT strategy for mascope web-based interface, 
and bearer transport with database access tokens for the mascope_sdk jupyter library authentication.
"""

from rich.pretty import pretty_repr
from fastapi import HTTPException, Request, status
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
from mascope_server.api.new.auth.access_token.util import get_token_service
from mascope_server.runtime import runtime


# Cookie-based authentication for the web app
auth_backend_jwt = AuthenticationBackend(
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
    request_service_name = request.headers.get("x-service-name")

    # Access the route function (endpoint handler)
    route_func = request.scope.get("endpoint")

    # Cookie-based JWT for Mascope web app access
    if cookie_auth:
        runtime.logger.debug("Using web application authentication.")
        return [auth_backend_jwt]

    # Access token-based authentication(mascope_sdk Jupyter lib, file_converter service, tof-agent)
    if auth_header and not cookie_auth:
        token = auth_header.split(" ")[1]
        token_service_name = await get_token_service(token)

        if token_service_name != request_service_name:
            runtime.logger.error(
                f"Token service name '{token_service_name}' "
                f"mismatch request service name '{request_service_name}'. "
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=(
                    "Unauthorized. The provided token is not authorized for this service. "
                    "Please try to refresh the token."
                ),
            )

        # Check if the endpoint allows for token access
        if hasattr(route_func, "token_access") and route_func.token_access:
            runtime.logger.debug(f"Using {token_service_name} authentication protocol.")
            return [auth_backend_access_token]
        else:
            runtime.logger.error(
                f"This endpoint is not configured for {token_service_name} access."
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Access denied. Resource is not available, please contact your administrator.",
            )

    # No valid authentication credentials found
    runtime.logger.error("Request did not contain a valid authentication credentials.")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized. Please log in through Mascope web interface or provide a valid API token.",
    )
