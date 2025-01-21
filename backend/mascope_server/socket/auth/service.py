"""Core Socket.IO authentication functionality."""

from typing import Optional
from mascope_server.api.new.auth.config import auth_settings
from mascope_server.socket.auth.token import (
    validate_jwt_token,
    validate_service_access_token,
)
from mascope_server.socket.auth.session import clear_user_session, save_user_session
from mascope_server.socket.auth.exceptions import (
    SocketAuthConfigError,
    SocketForbiddenError,
    SocketUnauthenticatedError,
)
from mascope_server.runtime import runtime


async def verify_role_permission(user, minimum_role: str) -> None:
    """
    Verify if user has sufficient role permissions.

    :param user: User instance to verify
    :param minimum_role: Minimum role required
    :raises SocketAuthConfigError: If role configuration is invalid
    :raises SocketForbiddenError: If user's role is insufficient
    """
    required_role_id = auth_settings.ROLE_ACCESS_LEVELS.get(minimum_role)
    if required_role_id is None:
        runtime.logger.error(f"Invalid role configuration: {minimum_role}")
        raise SocketAuthConfigError()

    if user.role_id < required_role_id:
        raise SocketForbiddenError()


async def authenticate_socket_connection(
    sid: str,
    token: str,
    minimum_role: str,
    service_name: Optional[str] = None,
) -> None:
    """
    Authenticate Socket.IO connection.

    Validates the client's connection by:
    1. Validating the token based on service type
    2. Retrieving associated user
    3. Verifying user's role meets minimum requirements
    4. Updating socket session with user data

    :param sid: Socket.IO session ID
    :type sid: str
    :param token: Authentication token (JWT for frontend, access token for services)
    :type token: str
    :param minimum_role: Minimum role required for this connection
    :type minimum_role: str
    :param service_name: Name of the service requesting authentication (if applicable)
    :type service_name: Optional[str]
    :raises SocketUnauthenticatedError: If authentication fails
    :raises SocketForbiddenError: If user's role is insufficient
    :raises SocketAuthConfigError: If role configuration is invalid
    """
    namespace = f"/{service_name}" if service_name else "/"
    try:
        # Step 1: Clear any existing session first to prevent stale data
        await clear_user_session(sid=sid, namespace=namespace)

        # Step 2: Validate provided authentication token
        if service_name:
            # Service authentication (e.g., tof-agent)
            user = await validate_service_access_token(token, service_name)
        else:
            # Frontend user authentication
            user = await validate_jwt_token(token)

        # Step 3: Verify role permissions
        await verify_role_permission(user, minimum_role)

        # Step 4: Save user session
        await save_user_session(sid, user, namespace=namespace)
        runtime.logger.debug(
            f"{service_name.title() if service_name else 'User'} socket session {sid} "
            f"authenticated by user '{user.username}'"
        )
    except Exception as e:
        # Handle authentication error and clean up session."""
        await clear_user_session(sid=sid, namespace=namespace)

        if isinstance(e, (SocketForbiddenError, SocketAuthConfigError)):
            raise SocketUnauthenticatedError(str(e)) from e
        if isinstance(e, SocketUnauthenticatedError):
            raise

        runtime.logger.error(f"Socket authentication failed: {str(e)}")
        raise SocketUnauthenticatedError("Authentication failed") from e
