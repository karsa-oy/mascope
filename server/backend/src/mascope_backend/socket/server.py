"""Socket.IO server initialization and configuration."""

import socketio
from mascope_backend.socket.logging import get_socket_logger
from mascope_backend.runtime import runtime


def create_socket_server() -> socketio.AsyncServer:
    """
    Create Socket.IO server with Redis for multi-worker coordination.

    Sets up:
    - AsyncRedisManager for cross-worker event routing (pub/sub)
    - Falls back to single-worker mode if Redis is unavailable.

    NOTE: Separate Redis client handles session storage
    (see RedisSessionClient in redis_session_client.py)

    :return: Configured Socket.IO server instance
    :rtype: socketio.AsyncServer
    """
    client_manager = None

    # Setup Redis manager for pub/sub coordination
    if redis_url := (runtime.config.redis and runtime.config.redis.get_url()):
        try:
            client_manager = socketio.AsyncRedisManager(redis_url)
            runtime.logger.info(f"Socket server: Using Redis manager at {redis_url}")
        except Exception as e:
            runtime.logger.error(f"Failed to create Redis manager: {e}")
            runtime.logger.warning("Falling back to single-worker mode")
    else:
        runtime.logger.info("Socket server: No Redis configured (single-worker mode)")

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
