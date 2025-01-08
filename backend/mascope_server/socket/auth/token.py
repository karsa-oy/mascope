"""JWT token validation and extraction."""

import re
from mascope_server.api.new.auth.backend import auth_backend_cookie
from mascope_server.socket.auth.exceptions import SocketUnauthenticatedError
from mascope_server.runtime import runtime

# JWT token pattern (header.payload.signature)
JWT_PATTERN = re.compile(r"^[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+$")


async def get_jwt_from_cookies(cookies: str) -> str:
    """
    Extract authentication token from cookie string.

    :param cookies: Raw cookie string from HTTP headers
    :type cookies: str
    :raises HTTPException: If auth cookie is not found
    :return: JWT token string
    :rtype: str
    """
    try:
        cookie_dict = {
            c.split("=")[0].strip(): c.split("=")[1].strip() for c in cookies.split(";")
        }
    except Exception as e:
        raise SocketUnauthenticatedError("Invalid cookie format") from e

    jwt_token = cookie_dict.get("mascope_auth")
    if not jwt_token:
        raise SocketUnauthenticatedError("Authentication cookie not found")

    return jwt_token


async def validate_jwt_token(jwt_token: str):
    """
    Validate JWT token and return associated user.

    Verifies the provided JWT token using the configured authentication strategy
    and retrieves the associated user from the database.

    :param jwt_token: JWT token string from client cookie
    :type jwt_token: str
    :return: User instance if token is valid, None otherwise
    :rtype: Optional[User]
    """
    try:
        # Step 1. Basic token format validation
        if not isinstance(jwt_token, str):
            raise SocketUnauthenticatedError("Invalid token format: not a string")
        if not JWT_PATTERN.match(jwt_token):
            raise SocketUnauthenticatedError("Invalid token format: not a JWT token")

        # Step 2. Token validation using cookie strategy
        # TODO Late import to avoid circular dependencies
        from mascope_server.api.new.users.user_manager.util import (
            get_user_manager_context,
        )

        jwt_strategy = auth_backend_cookie.get_strategy()

        async with get_user_manager_context() as user_manager:
            user = await jwt_strategy.read_token(jwt_token, user_manager)
            if not user:
                raise SocketUnauthenticatedError(
                    "Token validation failed: user not found"
                )
            return user
    except SocketUnauthenticatedError:
        raise
    except Exception as e:
        runtime.logger.error(f"Token validation failed: {str(e)}")
        raise SocketUnauthenticatedError("Token validation failed") from e
