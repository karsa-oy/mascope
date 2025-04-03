from fastapi import HTTPException, status


class InvalidRoleException(HTTPException):
    """
    Exception for Invalid Role (500) when a role is not defined in ROLE_ACCESS_LEVELS.
    Indicates a configuration issue or a bug.
    """

    def __init__(self, detail="The required role is not defined in the configuration."):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail
        )
