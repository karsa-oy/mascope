"""
Route dependencies
"""

from fastapi import Depends

from mascope_backend.api.new.auth import fastapi_users, get_enabled_backends
from mascope_backend.api.new.auth.config import auth_settings
from mascope_backend.api.new.auth.exceptions import ForbiddenAccessException
from mascope_backend.api.new.roles.exceptions import InvalidRoleException
from mascope_backend.db import User


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


async def owner_user(user: User = Depends(current_superuser)) -> User:
    return await role_based_access(user, "owner")


async def role_based_access(user: User, access: str) -> User:
    """
    Enforces role-based access control by comparing the user's role_id with the required access level.

    :param user: The current active user.
    :param access: Name of the required role (e.g., "admin", "editor").
    :raises HTTPException: If the user's role does not meet the required level.
    :return: The user object if the role requirement is met.
    """
    role_access_levels = auth_settings.ROLE_ACCESS_LEVELS
    # Get the required role level
    required_role_id = role_access_levels.get(access, None)
    if required_role_id is None:
        raise InvalidRoleException(
            detail=f"The required role '{access}' is not defined in the configuration."
        )

    # Validate user's role_id
    if user.role_id is None or user.role_id not in role_access_levels.values():
        raise InvalidRoleException(
            detail=f"The user's role ID '{user.role_id}' is not defined in the configuration. Please check for configuration issues."
        )

    # Enforce role-based access
    if user.role_id < required_role_id:
        raise ForbiddenAccessException()

    return user
