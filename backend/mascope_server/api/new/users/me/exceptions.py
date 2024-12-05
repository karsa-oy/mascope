from fastapi import HTTPException, status


class PasswordMismatchException(HTTPException):
    """Exception raised when new password and verification do not match."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and verification do not match.",
        )


class SamePasswordException(HTTPException):
    """Exception raised when new password is same as current."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password.",
        )


class InvalidCurrentPasswordException(HTTPException):
    """Exception raised when current password verification fails."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )
