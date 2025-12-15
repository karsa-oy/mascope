"""Socket.IO storage for cross-worker state management.

This module provides Redis-backed storage for socket state that must
be accessible across multiple uvicorn workers.

Components:
- RedisStorageClient: Shared Redis connection
- Session management: Authentication session CRUD operations
"""

from mascope_backend.socket.storage.client import (
    redis_storage_client,
)
from mascope_backend.socket.storage.sessions import (
    save_user_session,
    clear_user_session,
    get_session_user,
)

__all__ = [
    "redis_storage_client",
    "save_user_session",
    "clear_user_session",
    "get_session_user",
]
