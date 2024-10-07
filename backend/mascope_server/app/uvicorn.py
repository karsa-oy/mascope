import uvicorn
import os

from mascope_server.runtime import runtime


def run():
    """Entry point to run Mascope server"""
    expose = os.environ.get("MASCOPE_DEVHOST")
    host = "0.0.0.0" if (runtime.mode == "prod" or expose) else "localhost"
    runtime.logger.info(
        f"Starting uvicorn at {host}:{runtime.meta.api_port} in {runtime.mode} mode"
    )
    if expose:
        runtime.logger.warning("Exposing dev server to the network")
    # start uvicorn
    uvicorn.run(
        "mascope_server.app.socket_app:sio_app",
        host=host,
        port=runtime.meta.api_port,
        reload=(runtime.mode == "dev"),
        log_level="critical",
        use_colors=True,
    )
