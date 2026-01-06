"""
File converter service connection lifecycle.

Handles socket connections on the file-converter namespace. File converter connections
are not authenticated at connection since multiple users may trigger file conversions.
Instead, authentication happens per-event with the user data and access token being
passed in conversion events.
"""

import os

from mascope_backend.runtime import runtime
from mascope_backend.socket import sio


@sio.event(namespace="/file-converter")
async def connect(sid: str, environ: dict) -> bool:
    """
    Handle file converter service connections.
    Validates the service name at connection.

    :param sid: Socket session ID
    :type sid: str
    :param environ: WSGI environment containing request data
    :type environ: dict
    :return: Connection acceptance status
    :rtype: bool
    """
    worker_pid = os.getpid()
    try:
        service_name = environ.get("HTTP_X_SERVICE_NAME")
        if service_name == "file-converter":
            runtime.logger.debug(
                f"File converter service connected with sid {sid} [Worker {worker_pid}]"
            )
            return True
        else:
            runtime.logger.warning(
                f"Unexpected connection to file-converter namespace: {service_name} [Worker {worker_pid}]"
            )
            return False
    except Exception as e:
        runtime.logger.error(
            f"Error in file converter connection: {str(e)} [Worker {worker_pid}]"
        )
        return False


@sio.event(namespace="/file-converter")
async def disconnect(sid: str) -> None:
    """
    Handle file converter service disconnections.

    :param sid: Socket session ID
    :type sid: str
    """
    worker_pid = os.getpid()
    runtime.logger.debug(
        f"File converter service disconnected: {sid} [Worker {worker_pid}]"
    )
