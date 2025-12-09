"""Socket.IO server initialization and configuration."""

import socketio
from mascope_backend.socket.logging import get_socket_logger
from mascope_backend.runtime import runtime


def create_socket_server() -> socketio.AsyncServer:
    """
    Create Socket.IO server with Redis for multi-worker coordination.

    Redis is required for all deployment modes (dev/prod) as it handles:
    - Cross-worker Socket.IO event routing (pub/sub) - socketio.AsyncRedisManager redis client
    - Session storage and RBAC validation - RedisSessionClient (see redis_session_client.py)

    :return: Configured Socket.IO server instance
    :rtype: socketio.AsyncServer
    :raises RuntimeError: If Redis is not configured properly
    """
    if not runtime.config.redis or runtime.config.redis.get_url() is None:
        raise RuntimeError(
            "Redis configuration is required for Socket.IO server. "
            "Check that Redis is configured in your mascope.toml file."
        )
    redis_url = runtime.config.redis.get_url()

    try:
        client_manager = socketio.AsyncRedisManager(redis_url)
        runtime.logger.info(f"Socket server: Connected to Redis at {redis_url}")
    except Exception as e:
        raise RuntimeError(f"Failed to connect to Redis at {redis_url}: {e}.") from e

    return socketio.AsyncServer(
        async_mode="asgi",  # run in ASGI mode
        cors_allowed_origins="*",  # allow all origins
        client_manager=client_manager,  # Redis manager for multi-worker
        namespaces=[
            "/",  # default namespace for general communication user socket client -> mascope server
            "/file-converter",  # namespace for file converter service
            "/tof-agent",  # namespace for TOF-instrument agent
        ],
        ping_timeout=300,  # 5 minutes for ping response
        logger=get_socket_logger(),
        engineio_logger=False,
    )


# Main Socket.IO server instance
sio = create_socket_server()
