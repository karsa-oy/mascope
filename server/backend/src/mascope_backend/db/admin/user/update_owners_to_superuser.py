"""
Database operation for fixing owner users missing superuser rights.

This operation identifies owner-role users with is_superuser=False
and updates them to is_superuser=True, which is required for proper
permission handling.

Entry Points:
- Async: `fix_owner_superuser_rights()` for use in async code
- Sync: `run_fix_owner_superuser_rights()` for CLI and scripts
"""

import asyncio

from sqlalchemy import update

from mascope_backend.api.new.auth.config import auth_settings
from mascope_backend.db import User, async_session
from mascope_backend.runtime import runtime


async def update_owners_superuser_rights() -> dict:
    """
    Fix owner users missing superuser rights.

    Updates all users with owner role to is_superuser=True.

    :return: Operation results with count of fixed users
    :rtype: dict
    """
    owner_role_id = auth_settings.ROLE_ACCESS_LEVELS.get("owner")

    async with async_session() as session:
        update_result = await session.execute(
            update(User)
            .where(User.role_id == owner_role_id, ~User.is_superuser)
            .values(is_superuser=True)
        )

        fixed_count = update_result.rowcount
        await session.commit()

        if fixed_count == 0:
            message = "No owner users with missing superuser rights found"
            runtime.logger.debug(message)
        else:
            message = f"Fixed {fixed_count} owner user(s) with missing superuser rights"
            runtime.logger.info(message)

        return {
            "status": "success",
            "message": message,
            "data": {
                "fixed_count": fixed_count,
            },
        }


def run_update_owners_superuser_rights() -> dict:
    """
    Synchronous entry point for fixing owner superuser rights.

    Wrapper around async `update_owners_superuser_rights()` for use in
    synchronous contexts such as CLI commands or standalone scripts.

    :return: Operation results
    :rtype: dict
    """
    return asyncio.run(update_owners_superuser_rights())
