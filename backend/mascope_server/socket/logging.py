import logging
import inspect
from mascope_server.runtime import runtime

logger = runtime.logger.bind(method="EVENT")


class SocketLoggingHandler(logging.Handler):
    # based on https://loguru.readthedocs.io/en/stable/overview.html#entirely-compatible-with-standard-logging
    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists.
        level: str | int
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message.
        frame, depth = inspect.currentframe(), 0
        while frame and (depth == 0 or frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def get_socket_logger():
    wrapped_logger = logging.Logger("sio_logger", level=0)
    wrapped_logger.addHandler(SocketLoggingHandler())
    return wrapped_logger
