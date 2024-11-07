""" 
Route dependencies  
"""

from fastapi import Depends, HTTPException, status
from mascope_server.db.models import User
from mascope_server.api.new.auth.auth_backend import fastapi_users, get_enabled_backends

# Dependencies for active, verified, and superuser users
current_user = fastapi_users.current_user(get_enabled_backends=get_enabled_backends)
current_active_user = fastapi_users.current_user(
    active=True, get_enabled_backends=get_enabled_backends
)
current_active_verified_user = fastapi_users.current_user(
    active=True, verified=True, get_enabled_backends=get_enabled_backends
)
current_superuser = fastapi_users.current_user(
    active=True, superuser=True, get_enabled_backends=get_enabled_backends
)

get_current_user_token = fastapi_users.authenticator.current_user_token(active=True)


# Dependency to check if the user is an admin
async def admin_user(user: User = Depends(current_active_user)) -> User:
    """
    Custom dependency to ensure that the user has admin privileges.

    This function checks if the current user has the "admin" role (role_id == 2).
    If the user is not an admin, it raises a 403 HTTP exception.

    :param user: The current active user.
    :type user: User
    :raises HTTPException: If the user does not have the admin role.
    :return: The user object, if the user is an admin.
    :rtype: User
    """
    # Assuming the role is stored in user.role.name
    if user.role_id is None or user.role_id != 2:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource.",
        )
    return user
