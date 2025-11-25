import os
import uvicorn
from mascope_backend.runtime import runtime


def run():
    """Entry point to run Mascope server"""
    expose = os.environ.get("MASCOPE_DEVHOST")
    host = "0.0.0.0" if (runtime.mode == "prod" or expose) else "localhost"

    workers = runtime.config.get_worker_count()

    if runtime.mode == "dev" and workers > 1:
        runtime.logger.warning(
            f"You are using {workers} uvicorn workers which may cause memory issues on Windows. "
            f"Uvicorn has port-sharing issues on Windows which may lead to occasional http timeouts. "
            f"Consider using a single worker in development."
        )

    # reload only works with single worker
    enable_reload = runtime.mode == "dev" and workers == 1

    runtime.logger.info(
        f"Starting uvicorn at {host}:{runtime.meta.api_port} "
        f"in {runtime.mode} mode with {workers} worker(s)"
    )

    if enable_reload:
        runtime.logger.info("Hot reload: ENABLED")
    elif runtime.mode == "dev":
        runtime.logger.info("Hot reload: DISABLED (multi-worker mode)")

    if expose:
        runtime.logger.warning("Exposing dev server to the network")

    uvicorn.run(
        "mascope_backend.app.socket_app:sio_app",
        host=host,
        port=runtime.meta.api_port,
        workers=workers,
        reload=enable_reload,
        log_level="critical",
        use_colors=True,
    )
