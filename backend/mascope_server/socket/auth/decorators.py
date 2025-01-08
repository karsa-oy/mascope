"""Socket authentication decorators."""

from functools import wraps
from typing import Callable
from mascope_server.api.new.auth.config import auth_settings
from mascope_server.socket.auth.session import get_session_user
from mascope_server.socket.auth.exceptions import (
    SocketAuthError,
    SocketForbiddenError,
    SocketAuthConfigError,
)
from mascope_server.runtime import runtime


def socket_auth(minimum_role: str):
    """
    Decorator for Socket.IO event handlers that enforces role-based access control.

    :param minimum_role: Minimum role required to access this event
    :type minimum_role: str
    """

    def decorator(handler: Callable):
        @wraps(handler)
        async def wrapper(sid: str, *args, **kwargs):
            try:
                session = await get_session_user(sid)

                required_role_id = auth_settings.ROLE_ACCESS_LEVELS.get(minimum_role)
                if required_role_id is None:
                    runtime.logger.error(f"Invalid role configuration: {minimum_role}")
                    raise SocketAuthConfigError()

                if session["role_id"] < required_role_id:
                    raise SocketForbiddenError()

                return await handler(sid, *args, **kwargs)

            except SocketAuthError as e:
                runtime.logger.error(f"Socket auth error for {sid}: {str(e)}")

            except Exception as e:
                runtime.logger.error(f"Unexpected socket auth error: {str(e)}")

        return wrapper

    return decorator
