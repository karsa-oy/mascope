"""
Service presence tracking with Redis storage.

Tracks which backend services (e.g., file-converter) are connected via
Socket.IO. Each service writes a Redis key on connect and deletes it on
disconnect, allowing any worker to check service availability.

Lifecycle is managed by Socket.IO connect/disconnect handlers.
Socket.IO ping_timeout guarantees disconnect fires even
on ungraceful shutdown.
"""

import os

from mascope_backend.runtime import runtime
from mascope_backend.socket.storage.client import redis_storage_client
from mascope_backend.socket.storage.config import storage_config


async def register_service(service_name: str, sid: str) -> None:
    """
    Register a service as connected in Redis.

    Called from the Socket.IO connect handler when a service successfully
    authenticates on its namespace.

    :param service_name: Service identifier (e.g., "file-converter")
    :type service_name: str
    :param sid: Socket.IO session ID of the connected service
    :type sid: str
    """
    worker_pid = os.getpid()
    key = storage_config.service_key(service_name)

    try:
        await redis_storage_client.client.set(key, sid)
        runtime.logger.debug(
            f"Service '{service_name}' registered (sid={sid}) [Worker {worker_pid}]"
        )
    except Exception as e:
        runtime.logger.error(
            f"Failed to register service '{service_name}': {e} [Worker {worker_pid}]"
        )


async def unregister_service(service_name: str) -> None:
    """
    Remove a service's presence key from Redis.

    Called from the Socket.IO disconnect handler when a service disconnects.

    :param service_name: Service identifier (e.g., "file-converter")
    :type service_name: str
    """
    worker_pid = os.getpid()
    key = storage_config.service_key(service_name)

    try:
        await redis_storage_client.client.delete(key)
        runtime.logger.debug(
            f"Service '{service_name}' unregistered [Worker {worker_pid}]"
        )
    except Exception as e:
        runtime.logger.error(
            f"Failed to unregister service '{service_name}': {e} [Worker {worker_pid}]"
        )


async def is_service_connected(service_name: str) -> bool:
    """
    Check if a service is currently connected (cross-worker).

    Reads a Redis key that is set on connect and deleted on disconnect.
    Works from any worker because Redis is shared state.

    :param service_name: Service identifier (e.g., "file-converter")
    :type service_name: str
    :return: True if the service has an active connection
    :rtype: bool
    """
    key = storage_config.service_key(service_name)

    try:
        return bool(await redis_storage_client.client.exists(key))
    except Exception as e:
        runtime.logger.error(f"Failed to check service '{service_name}' presence: {e}")
        return False
