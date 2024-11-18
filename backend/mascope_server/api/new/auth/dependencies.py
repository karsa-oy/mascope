""" 
Route dependencies  
"""

from fastapi import Depends
from mascope_server.api.new.auth.exceptions import (
    ForbiddenAccessException,
    InvalidRoleException,
)
from mascope_server.db.models import User
from mascope_server.api.new.auth.config import auth_settings
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


# Role-based access dependencies
async def guest_user(user: User = Depends(current_active_user)) -> User:
    return await role_based_access(user, "guest")


async def editor_user(user: User = Depends(current_active_user)) -> User:
    return await role_based_access(user, "editor")


async def admin_user(user: User = Depends(current_active_user)) -> User:
    return await role_based_access(user, "admin")


async def owner_user(user: User = Depends(current_active_user)) -> User:
    return await role_based_access(user, "owner")


async def role_based_access(user: User, access: str) -> User:
    """
    Enforces role-based access control by comparing the user's role_id with the required access level.

    :param user: The current active user.
    :param access: Name of the required role (e.g., "admin", "editor").
    :raises HTTPException: If the user's role does not meet the required level.
    :return: The user object if the role requirement is met.
    """
    required_role_id = auth_settings.ROLE_ACCESS_LEVELS.get(access, None)

    if required_role_id is None:
        raise InvalidRoleException()

    if user.role_id is None or user.role_id < required_role_id:
        raise ForbiddenAccessException()
    return user
