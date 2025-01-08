"""Core Socket.IO authentication functionality."""

from mascope_server.socket.auth.token import get_jwt_from_cookies, validate_jwt_token
from mascope_server.socket.auth.session import clear_user_session, save_user_session
from mascope_server.socket.auth.exceptions import SocketUnauthenticatedError
from mascope_server.runtime import runtime


async def authenticate_socket_connection(
    sid: str,
    environ: dict,
) -> None:
    """
    Authenticate Socket.IO connection.

    Validates the client's connection by:
    1. Extracting JWT token from cookies
    2. Validating the token and retrieving user
    3. Setting up socket session with user data

    :param sid: Socket.IO session ID
    :type sid: str
    :param environ: WSGI environment dictionary containing request data
    :type environ: dict
    :raises SocketUnauthenticatedError: If authentication fails
    """
    try:
        # Step 1: Clear any existing session first to prevent stale data
        await clear_user_session(sid)

        # Step 2: Get cookies from environment
        cookies = environ.get("HTTP_COOKIE")
        if not cookies:
            raise SocketUnauthenticatedError("No cookies in request")

        # Step 3: Extract JWT token
        jwt_token = await get_jwt_from_cookies(cookies)

        # Step 4 Validate token and get user
        user = await validate_jwt_token(jwt_token)

        # Step 5: Save user session
        await save_user_session(sid, user)
        runtime.logger.debug(
            f"Socket client id {sid} is authenticated as user `{user.username}`"
        )

    except SocketUnauthenticatedError:
        await clear_user_session(sid)
        # Re-raise authentication errors
        raise
    except Exception as e:
        runtime.logger.error(f"Socket authentication failed: {str(e)}")
        raise SocketUnauthenticatedError("Authentication failed") from e
