"""
Utility module for cleaning invalid access tokens from the database.

It provides two entry points:
- An async function `clean_access_tokens()` for use by other async code
- A sync function `run_clean_access_tokens()` as the Poetry command entry point
"""

import asyncio
from mascope_backend.db import (
    async_session,
    configure_database_engine,
)
from mascope_backend.db.models import AccessToken
from mascope_backend.db.utils import get_current_db_version
from mascope_backend.db.ops.backup import create_db_backup
from mascope_backend.runtime import runtime


async def clean_access_tokens() -> int:
    """
    Clean up invalid access tokens from the database.

    This function removes tokens with:
    1. NULL service names
    2. Service names not in the allowed list

    Assumes a database connection is already established.
    Creates a backup before making changes.

    :return: Number of deleted tokens
    :rtype: int
    """
    async with async_session() as session:
        deleted_count = await AccessToken.clean_invalid_tokens(session)
        if deleted_count > 0:
            runtime.logger.info(
                f"🗑️ Deleted {deleted_count} access tokens with invalid or NULL service names."
            )
        else:
            runtime.logger.info("✅ No invalid access tokens found.")
        return deleted_count


async def init_db_and_clean_tokens() -> int:
    """
    Initialize the database connection and clean invalid tokens.

    Used when running as a standalone command where no database
    connection has been established yet.

    :return: Number of deleted tokens
    :rtype: int
    """
    # Configure the database engine
    current_version = get_current_db_version()
    await configure_database_engine(current_version)

    # Create a backup before any changes
    await create_db_backup()

    # Now async_session is configured -> usual async flow can be continued
    return await clean_access_tokens()


def run_db_clean_access_tokens():
    """
    Synchronous entry point for the Poetry command 'mascope-clean-access-tokens'.

    Initializes the database connection and runs the token cleaning process.
    """
    asyncio.run(init_db_and_clean_tokens())


if __name__ == "__main__":
    run_db_clean_access_tokens()
