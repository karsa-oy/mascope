"""
Maintenance script to fix owner users missing superuser rights.

Bug #1211 - When owners registered new owner users, the is_superuser flag
was not automatically set to True, causing 403 Forbidden errors when they
tried to manage other users.

Usage:
    uv run python -m mascope_backend.db.maintenance_scripts.restore_owner_superuser_rights

Date: 2025-10-23
Issue: #1211
"""

import asyncio
from sqlalchemy import select

from mascope_backend.db import async_session, configure_database_engine
from mascope_backend.db.models import User
from mascope_backend.db.ops.user.update_owners_to_superuser import (
    update_owners_superuser_rights,
)
from mascope_backend.db.utils import get_current_db_version
from mascope_backend.api.new.auth.config import auth_settings
from mascope_backend.runtime import runtime


async def find_affected_users() -> list[User]:
    """
    Find owner users with missing superuser rights.

    :return: List of affected User model instances
    """
    owner_role_id = auth_settings.ROLE_ACCESS_LEVELS.get("owner")

    async with async_session() as session:
        query = select(User).where(
            User.role_id == owner_role_id, User.is_superuser == 0
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


def get_user_confirmation() -> bool:
    """
    Prompt for confirmation.

    :return: True if confirmed
    """
    print("This will set is_superuser=True for the above owner users.")

    while True:
        response = input("Proceed with fix? (yes/no): ").strip().lower()
        if response in ("yes", "y"):
            return True
        if response in ("no", "n"):
            return False
        print("Please answer 'yes' or 'no'")


async def run_fix() -> None:
    """Find affected users, confirm, and fix them."""
    current_db_version = get_current_db_version()
    if current_db_version is None:
        runtime.logger.error("No database found. Please create a database first.")
        return

    await configure_database_engine(current_db_version)
    runtime.logger.info(f"Connected to database v{current_db_version}")

    affected_users = await find_affected_users()

    if not affected_users:
        runtime.logger.info(
            "No owner users with missing superuser rights found. Nothing to restore."
        )
        return

    display_affected_users(affected_users)

    if not get_user_confirmation():
        runtime.logger.info("Restore cancelled by user")
        return

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
