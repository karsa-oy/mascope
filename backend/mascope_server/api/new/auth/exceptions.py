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


class InvalidRoleException(HTTPException):
    """
    Exception for Invalid Role (500) when a role is not defined in ROLE_ACCESS_LEVELS.
    Indicates a configuration issue or a bug.
    """

    def __init__(
        self,
        detail: str = "Role is not defined. Please check the configuration.",
    ):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail
        )
