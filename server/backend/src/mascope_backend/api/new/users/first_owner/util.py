from sqlalchemy import func, select
from mascope_backend.db import async_session
from mascope_backend.db.models import User
from mascope_backend.api.new.auth.config import auth_settings
from mascope_backend.api.new.users.first_owner.exceptions import (
    LastOwnerDeletionException,
    LastOwnerDowngradeException,
    FirstOwnerRegistrationNotAvailableException,
)


async def check_first_owner_registration():
    """
    Check if owner registration is available, i.e. if no users exist.

    :raises FirstOwnerRegistrationNotAvailableException: If any users exist in the system
    """
    async with async_session() as session:
        query = select(func.count()).select_from(User)  # pylint: disable=not-callable
        result = await session.execute(query)
        count = result.scalar()
    if count > 0:
        raise FirstOwnerRegistrationNotAvailableException()


async def check_last_owner_deletion(user_id: int):
    """
    Check if deleting the specified user would remove the last owner.

    :param user_id: ID of the user being deleted
    :raises LastOwnerDeletionException: If this is the last owner user
    """
    async with async_session() as session:
        # Check if user is an owner
        user_query = select(User.role_id).where(User.id == user_id)
        result = await session.execute(user_query)
        role_id = result.scalar()

        if role_id == auth_settings.ROLE_ACCESS_LEVELS["owner"]:
            # Count other owners
            if (await User.count_other_owners(session, user_id)) == 0:
                raise LastOwnerDeletionException()


async def check_owner_role_change(user_id: int, new_role_id: int):
    """
    Check if changing user's role would remove the last owner.

    :param user_id: ID of the user being updated
    :param new_role_id: New role ID to be assigned
    :raises LastOwnerDowngradeException: If this would remove the last owner
    """
    async with async_session() as session:
        # Check if user is currently an owner
        user_query = select(User.role_id).where(User.id == user_id)
        result = await session.execute(user_query)
        current_role_id = result.scalar()

        if (
            current_role_id == auth_settings.ROLE_ACCESS_LEVELS["owner"]
            and new_role_id != auth_settings.ROLE_ACCESS_LEVELS["owner"]
        ):
            # Count other owners
            if (await User.count_other_owners(session, user_id)) == 0:
                raise LastOwnerDowngradeException()
