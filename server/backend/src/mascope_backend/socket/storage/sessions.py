"""
Socket.IO session management with Redis storage.

Stores authentication sessions in Redis for cross-worker access.
Each session contains user_id, username, and role_id for RBAC checks.

Sessions persist for a configurable TTL (default 24 hours) as a safety net.
Primary cleanup occurs on socket disconnect. TTL is refreshed on each
access to keep active users authenticated indefinitely.
"""

import json
import os
from typing import Any
from mascope_backend.db.models import User
from mascope_backend.socket.storage.client import redis_storage_client
from mascope_backend.socket.auth.exceptions import SocketSessionError
from mascope_backend.runtime import runtime


def _build_session_key(sid: str, namespace: str = "/") -> str:
    """
    Build Redis key for session storage.

    :param sid: Socket.IO session ID
    :type sid: str
    :param namespace: Socket.IO namespace
    :type namespace: str
    :return: Redis key in format 'mascope:session:{namespace}:{sid}'
    :rtype: str
    """
    return f"mascope:session:{namespace}:{sid}"


async def save_user_session(sid: str, user: User, namespace: str = "/") -> None:
    """
    Save authenticated user session to Redis.

    Stores user authentication data (user_id, username, role_id) in Redis
    with automatic expiration. Sessions are accessible from any worker for
    RBAC checks. TTL acts as a safety net for orphaned sessions; primary
    cleanup occurs on socket disconnect.

    :param sid: Socket.IO session ID
    :type sid: str
    :param user: Authenticated user instance
    :type user: User
    :param namespace: Socket.IO namespace
    :type namespace: str
    :raises SocketSessionError: If session cannot be saved to Redis
    """
    try:
        worker_pid = os.getpid()
        session_key = _build_session_key(sid, namespace)
        session_data = {
            "user_id": user.id,
            "username": user.username,
            "role_id": user.role_id,
        }

        # TTL from config (default 24 hours)
        session_ttl = runtime.config.redis.session_ttl

        # Store in Redis with TTL
        await redis_storage_client.client.setex(
            session_key,
            session_ttl,
            json.dumps(session_data),
        )

        runtime.logger.debug(
            f"Redis session storage client: saved session for {sid}: user={user.username}, role_id={user.role_id} [Worker {worker_pid}]"
        )

    except Exception as e:
        runtime.logger.error(
            f"Redis session storage client: failed to save session for SID '{sid}': {str(e)} [Worker {worker_pid}]"
        )
        raise SocketSessionError("Failed to save session") from e


async def clear_user_session(sid: str, namespace: str = "/") -> None:
    """
    Clear user session from Redis.

    Removes authentication data for the given session ID. Called on
    disconnect or logout to immediately invalidate the session.

    :param sid: Socket.IO session ID
    :type sid: str
    :param namespace: Socket.IO namespace
    :type namespace: str
    """
    worker_pid = os.getpid()
    try:
        session_key = _build_session_key(sid, namespace)
        deleted = await redis_storage_client.client.delete(session_key)

        if deleted:
            runtime.logger.debug(
                f"Redis session storage client: cleared session for {sid} [Worker {worker_pid}]"
            )
        else:
            runtime.logger.trace(
                f"Redis session storage client: no session found to clear for {sid} [Worker {worker_pid}]"
            )

    except Exception as e:
        runtime.logger.error(
            f"Redis session storage client: failed to clear session for {sid}: {e} [Worker {worker_pid}]"
        )


async def get_session_user(sid: str, namespace: str = "/") -> dict[str, Any]:
    """
    Get user authentication data from Redis session.

    Retrieves stored user_id, username, and role_id for RBAC checks.
    Works across all workers since data is in Redis. Automatically
    refreshes the session TTL on each access to keep active users
    authenticated indefinitely.

    :param sid: Socket.IO session ID
    :type sid: str
    :param namespace: Socket.IO namespace
    :type namespace: str
    :return: User session data containing user_id, username, role_id
    :rtype: dict[str, Any]
    :raises SocketSessionError: If session not found or invalid
    """
    worker_pid = os.getpid()
    try:
        session_key = _build_session_key(sid, namespace)

        # Get session data
        if not (data := await redis_storage_client.client.get(session_key)):
            runtime.logger.debug(
                f"Redis session storage client: no session found for {sid} [Worker {worker_pid}]"
            )
            raise SocketSessionError("No session found")

        # Parse session
        session = json.loads(data)

        # Validate required fields
        if not isinstance(session.get("role_id"), int):
            raise SocketSessionError("Invalid session: missing or invalid role_id")

        # Refresh TTL on access (keeps active users sessions authenticated)
        session_ttl = runtime.config.redis.session_ttl
        await redis_storage_client.client.expire(session_key, session_ttl)

        runtime.logger.trace(
            f"Redis session storage client: retrieved session for {sid}, TTL refreshed [Worker {worker_pid}]"
        )

        return session

    except json.JSONDecodeError as e:
        runtime.logger.error(
            f"Redis session storage client: failed to decode session data for {sid}: {e} [Worker {worker_pid}]"
        )
        raise SocketSessionError("Corrupted session data") from e
    except SocketSessionError:
        raise
    except Exception as e:
        runtime.logger.error(
            f"Redis session storage client: session error for {sid}: {e} [Worker {worker_pid}]"
        )
        raise SocketSessionError(f"Session error: {e}") from e
