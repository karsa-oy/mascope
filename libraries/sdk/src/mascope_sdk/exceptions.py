"""Custom exceptions for the Mascope SDK."""


class MascopeError(Exception):
    """Base exception for all Mascope SDK errors."""

    pass


class ConfigurationError(MascopeError):
    """Raised when SDK configuration is invalid or missing.

    This includes missing environment variables, invalid URLs, or missing credentials.
    """

    pass


class MascopeAPIError(MascopeError):
    """Base exception for API-related errors.

    :ivar status_code: HTTP status code from the API response.
    :vartype status_code: int | None
    :ivar message: Error message from the API or a default message.
    :vartype message: str
    :ivar url: The URL that was being accessed when the error occurred.
    :vartype url: str | None
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        url: str | None = None,
    ):
        self.status_code = status_code
        self.message = message
        self.url = url
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        parts = [self.message]
        if self.status_code:
            parts.insert(0, f"[HTTP {self.status_code}]")
        if self.url:
            parts.append(f"(URL: {self.url})")
        return " ".join(parts)


class AuthenticationError(MascopeAPIError):
    """Raised when authentication fails (401/403 responses).

    This typically means the access token is invalid, expired, or missing.
    """

    pass


class NotFoundError(MascopeAPIError):
    """Raised when a requested resource is not found (404 response)."""

    pass


class ValidationError(MascopeAPIError):
    """Raised when request validation fails (422 response).

    This typically means the request parameters were invalid.
    """

    pass


class ServerError(MascopeAPIError):
    """Raised when the server encounters an error (5xx responses)."""

    pass


class MascopeConnectionError(MascopeError):
    """Raised when unable to connect to the Mascope server.

    This includes network errors, DNS failures, and timeouts.
    """

    def __init__(self, message: str, url: str | None = None):
        self.url = url
        super().__init__(f"{message}" + (f" (URL: {url})" if url else ""))


class MascopeTimeoutError(MascopeConnectionError):
    """Raised when a request times out."""

    pass
