"""Core Socket.IO authentication functionality."""

from typing import Optional
from mascope_server.socket.auth.token import (
    validate_jwt_token,
    validate_service_access_token,
)
from mascope_server.socket.auth.session import clear_user_session, save_user_session
from mascope_server.socket.auth.exceptions import SocketUnauthenticatedError
from mascope_server.runtime import runtime


async def authenticate_socket_connection(
    sid: str,
    token: str,
    service_name: Optional[str] = None,
) -> None:
    """
    Authenticate Socket.IO connection.

    Validates the client's connection by:
    1. Validating the token based on service type
    2. Retrieving associated user
    3. Updating socket session with user data

    :param sid: Socket.IO session ID
    :type sid: str
    :param token: Authentication token (JWT for frontend, access token for services)
    :type token: str
    :param service_name: Name of the service requesting authentication (if applicable)
    :type service_name: Optional[str]
    :raises SocketUnauthenticatedError: If authentication fails
    """
    try:
        if service_name:
            # Step 1: Clear any existing session first to prevent stale data
            await clear_user_session(sid=sid, namespace=f"/{service_name}")
            # Step 2: Service authentication (e.g., tof-agent)
            user = await validate_service_access_token(token)
            runtime.logger.debug(
                f"{service_name.title()} socket sesion {sid} authenticated by user '{user.username}'"
            )
            # Step 3: Save user session
            await save_user_session(sid, user, namespace=f"/{service_name}")
        else:
            # Step 1: Clear any existing session first to prevent stale data
            await clear_user_session(sid=sid)
            # Step 2: Frontend user authentication
            user = await validate_jwt_token(token)
            runtime.logger.debug(
                f"Socket session {sid} is authenticated by user `{user.username}`"
            )
            # Step 3: Save user session
            await save_user_session(sid, user)

    except SocketUnauthenticatedError:
        await clear_user_session(
            sid=sid, namespace=f"/{service_name}" if service_name else None
        )
        # Re-raise authentication errors
        raise
    except Exception as e:
        runtime.logger.error(f"Socket authentication failed: {str(e)}")
        raise SocketUnauthenticatedError("Authentication failed") from e
