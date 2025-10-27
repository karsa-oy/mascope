from sqlalchemy import func, select
from mascope_backend.db import async_session
from mascope_backend.db.models import User
from mascope_backend.api.new.auth.config import auth_settings
from mascope_backend.api.new.users.first_owner.exceptions import (
    LastOwnerDeletionException,
    LastOwnerDowngradeException,
)


async def check_first_owner_registration() -> bool:
    """
    Check if owner registration is available (no owner exists in system).

    Returns True if no owner role users exist, allowing first owner registration
    as a recovery mechanism even if non-owner users exist (edge case handling
    for manual DB modifications or migration issues).
    """
    async with async_session() as session:
        owner_count = await session.scalar(
            select(func.count())  # pylint: disable=not-callable
            .select_from(User)
            .where(User.role_id == auth_settings.ROLE_ACCESS_LEVELS["owner"])
        )
        return owner_count == 0


async def check_last_owner_deletion(user_id: int):
    """
    Check if deleting the specified user would remove the last owner.

    :param user_id: ID of the user being deleted
    :raises LastOwnerDeletionException: If this is the last owner user
    """
    async with async_session() as session:
        role_id = await session.scalar(select(User.role_id).where(User.id == user_id))

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
        current_role_id = await session.scalar(
            select(User.role_id).where(User.id == user_id)
        )

        if (
            current_role_id == auth_settings.ROLE_ACCESS_LEVELS["owner"]
            and new_role_id != auth_settings.ROLE_ACCESS_LEVELS["owner"]
            and await User.count_other_owners(session, user_id) == 0
        ):
            raise LastOwnerDowngradeException()
