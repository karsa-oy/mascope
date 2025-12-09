"""Redis client for cross-worker session storage.

Dedicated Redis client for storing Socket.IO authentication sessions
across multiple uvicorn workers. This client is separate from the AsyncRedisManager
used by Socket.IO for pub/sub coordination.
"""

from redis.asyncio import Redis, from_url
from mascope_backend.runtime import runtime


class RedisSessionClient:
    """
    Redis client manager for Socket.IO session storage.

    Manages a single Redis connection used exclusively for storing
    user authentication sessions across multiple workers.
    """

    def __init__(self):
        """Initialize Redis client (not connected)."""
        self._client: Redis | None = None

    async def connect(self) -> None:
        """
        Connect to Redis server.

        :raises RuntimeError: If Redis is not configured
        :raises ConnectionError: If Redis connection fails
        """
        if not runtime.config.redis or runtime.config.redis.get_url() is None:
            raise RuntimeError(
                "Redis configuration is required for session storage. "
                "Check that Redis is configured in your mascope.toml file."
            )

        redis_url = runtime.config.redis.get_url()

        try:
            self._client = from_url(redis_url, decode_responses=True)
            # Test connection
            await self._client.ping()

            ttl_hours = runtime.config.redis.session_ttl / 3600
            runtime.logger.info(
                f"Redis session client connected at {redis_url} "
                f"(session TTL: {ttl_hours:.1f} hours)"
            )
        except Exception as e:
            runtime.logger.error(f"Failed to connect Redis session client: {e}")
            raise ConnectionError(f"Redis connection failed: {e}") from e

    async def disconnect(self) -> None:
        """Close Redis connection gracefully."""
        if self._client:
            await self._client.aclose()
            runtime.logger.info("Redis session client disconnected")

    @property
    def client(self) -> Redis:
        """
        Get Redis client instance.

        :return: Connected Redis client
        :rtype: Redis
        :raises RuntimeError: If client is not connected
        """
        if not self._client:
            raise RuntimeError("Redis client not connected. Call connect() first.")
        return self._client


# Global Redis session client instance
redis_session_client = RedisSessionClient()
