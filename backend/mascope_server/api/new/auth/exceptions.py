from fastapi import HTTPException, status


class ForbiddenAccessException(HTTPException):
    """
    Exception for Forbidden (403) access.
    Used when a user does not have sufficient permissions to access a resource.
    """

    def __init__(
        self,
        detail: str = "You do not have the necessary permission to access this resource.",
    ):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
