"""
Maintenance script to fix owner users missing superuser rights.

Bug #1211 - When owners registered new owner users, the is_superuser flag
was not automatically set to True, causing 403 Forbidden errors when they
tried to manage other users.

Usage:
    mascope dev db script run restore_owner_superuser_rights
    mascope prod db script run restore_owner_superuser_rights

Date: 2025-10-23
Issue: #1211
"""

import asyncio

from sqlalchemy import select

from mascope_backend.api.new.auth.config import auth_settings
from mascope_backend.db import User, async_session, configure_database_engine
from mascope_backend.db.admin.user.update_owners_to_superuser import (
    update_owners_superuser_rights,
)
from mascope_backend.runtime import runtime


async def find_affected_users() -> list[User]:
    """
    Find owner users with missing superuser rights.

    :return: List of affected User model instances
    """
    owner_role_id = auth_settings.ROLE_ACCESS_LEVELS.get("owner")

    async with async_session() as session:
        query = select(User).where(
            (User.role_id == owner_role_id) & (~User.is_superuser)
        )
        result = await session.execute(query)
        return list(result.scalars().all())


def display_affected_users(users: list[User]) -> None:
    """
    Display affected users summary.

    :param users: List of User model instances
    """
    print(f"Found {len(users)} owner user(s) with missing superuser rights:")
    print("=" * 80)

    for i, user in enumerate(users, 1):
        print(f"\n{i}. {user.username}")
        print(f"   email: {user.email}")
        print(f"   ID: {user.id}")
        print(f"   is_superuser: {user.is_superuser}")

    print("=" * 80)
    print(f"Total: {len(users)} owner user(s) will be updated")


async def run_fix() -> None:
    """Find affected users, confirm, and fix them."""
    await configure_database_engine()

    affected_users = await find_affected_users()

    if not affected_users:
        runtime.logger.info(
            "No owner users with missing superuser rights found. Nothing to restore."
        )
        return

    display_affected_users(affected_users)

    runtime.logger.info("Executing fix...")
    result = await update_owners_superuser_rights()

    runtime.logger.info("=" * 80)
    runtime.logger.info("RESTORE COMPLETE")
    runtime.logger.info(f"Users updated: {result['data']['fixed_count']}")
    runtime.logger.info("=" * 80)


def main() -> None:
    """Entry point for the fix script."""
    try:
        asyncio.run(run_fix())
    except KeyboardInterrupt:
        runtime.logger.info("\nRestore cancelled by user (Ctrl+C)")
    except Exception:
        runtime.logger.exception("Restore script failed")
        raise


if __name__ == "__main__":
    main()
