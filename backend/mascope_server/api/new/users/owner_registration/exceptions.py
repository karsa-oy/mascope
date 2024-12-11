from fastapi import HTTPException, status


class InvalidServerOwnerSecretException(HTTPException):
    """
    Exception raised when the provided server owner secret is invalid.
    """

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid server owner secret provided.",
        )


class OwnerRegistrationNotAvailableException(HTTPException):
    """
    Exception raised when owner registration is not available
    (users already exist in the system).
    """

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner registration is not available.",
        )


class LastOwnerDeletionException(HTTPException):
    """Exception raised when attempting to delete the last owner user."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete the last owner user.",
        )


class LastOwnerDowngradeException(HTTPException):
    """Exception raised when attempting to downgrade the last owner user."""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot downgrade the last owner user.",
        )
