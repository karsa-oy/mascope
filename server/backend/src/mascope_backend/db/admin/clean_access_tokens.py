"""
Database administration operation for cleaning invalid access tokens.

Entry Points:
- Async: `clean_access_tokens()` for async callers (e.g. scheduled tasks)
- CLI: `mascope dev db script run clean_access_tokens`
"""

import asyncio

from mascope_backend.db import (
    AccessToken,
    async_session,
)
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


def run_clean_access_tokens() -> int:
    """
    Synchronous entry point for access token cleanup.

    :return: Number of deleted tokens
    :rtype: int
    """
    return asyncio.run(clean_access_tokens())
