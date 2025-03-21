from fastapi import HTTPException, status


class InternalServiceAccessException(HTTPException):
    """Exception for attempting to manage internal service tokens."""

    def __init__(
        self,
        detail: str = "This service token is managed internally and cannot be modified directly.",
    ):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )
