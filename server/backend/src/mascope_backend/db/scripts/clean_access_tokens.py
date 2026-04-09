"""
Maintenance script to clean invalid access tokens from the database.

Removes tokens with NULL or disallowed service names.

Usage:
    mascope dev db script run clean_access_tokens
    mascope prod db script run clean_access_tokens

Date: 2026-04-09
"""

import asyncio

from mascope_backend.db import configure_database_engine
from mascope_backend.db.admin.clean_access_tokens import clean_access_tokens
from mascope_backend.runtime import runtime


async def run() -> None:
    """Initialize database and clean invalid access tokens."""
    await configure_database_engine()
    deleted = await clean_access_tokens()
    runtime.logger.info("=" * 80)
    runtime.logger.info("CLEAN ACCESS TOKENS COMPLETE")
    runtime.logger.info(f"Deleted: {deleted}")
    runtime.logger.info("=" * 80)


def main() -> None:
    """Entry point for the token cleanup script."""
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        runtime.logger.info("Cancelled by user (Ctrl+C)")
    except Exception:
        runtime.logger.exception("Script failed")
        raise


if __name__ == "__main__":
    main()
