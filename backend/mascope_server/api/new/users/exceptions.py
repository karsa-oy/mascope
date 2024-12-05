from fastapi import HTTPException, status


class UsernameAlreadyExistsException(HTTPException):
    """
    Exception raised when a username already exists in the database.
    """

    def __init__(self, username: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The username '{username}' is already in use.",
        )


class UserEmailAlreadyExistsException(HTTPException):
    """
    Exception raised when a user with the provided email already exists in the database.
    """

    def __init__(self, email: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with the email '{email}' already exists.",
        )


class InvalidUsernameException(HTTPException):
    """
    Exception raised when the provided username is invalid (e.g., null or empty).
    """

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The username cannot be null or empty.",
        )


class InvalidFieldsException(HTTPException):
    """Exception raised when invalid fields are included to UserCreate, UserUpdate."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )
