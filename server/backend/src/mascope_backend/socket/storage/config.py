"""Socket storage configuration.

Centralized configuration for Redis-backed socket state storage including
session management and room tracking.
"""

from pydantic import BaseModel


class SocketStorageConfig(BaseModel):
    """
    Configuration for socket storage (sessions, rooms, etc.).

    Defines TTL values and Redis key prefixes for socket-related state.
    """

    # TTL settings (in seconds)
    session_ttl: int = 86400  # 24 hours - Socket session lifetime

    # Redis key prefixes
    session_key_prefix: str = "mascope:session:"  # Session storage keys

    def session_key(self, sid: str, namespace: str) -> str:
        """
        Build Redis key for session storage.

        :param sid: Socket.IO session ID
        :type sid: str
        :param namespace: Socket.IO namespace
        :type namespace: str
        :return: Redis key in format 'mascope:session:{namespace}:{sid}'
        :rtype: str
        """
        return f"{self.session_key_prefix}{namespace}:{sid}"


# Global storage config instance
storage_config = SocketStorageConfig()
