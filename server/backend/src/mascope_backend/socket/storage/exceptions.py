"""Socket storage exceptions."""


class SocketSessionError(Exception):
    """Raised when there are issues with socket session storage."""

    def __init__(self, message: str = "Session error"):
        self.message = message
        self.error_code = "SOCKET_SESSION_ERROR"
        super().__init__(message)
