import uvicorn

from mascope_server.runtime import runtime


def run():
    """Entry point to run Mascope server"""
    # start uvicorn
    uvicorn.run(
        "mascope_server.app.socket_app:sio_app",
        host=("0.0.0.0" if runtime.mode == "prod" else "localhost"),
        port=runtime.meta.api_port,
        reload=(runtime.mode == "dev"),
        log_level="critical",
        use_colors=True,
    )
