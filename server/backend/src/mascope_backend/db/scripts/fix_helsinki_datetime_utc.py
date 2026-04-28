"""
Maintenance script to fix datetime_utc values corrupted by the
Europe/Helsinki Docker timezone misconfiguration.

The container's local timezone was Europe/Helsinki instead of UTC, causing
processors to compute a non-zero utc_offset (2 h or 3 h depending on DST)
for files whose client PCs are in UTC.  The offset was applied twice: once
explicitly in Python, and again implicitly by PostgreSQL when the naive
timestamp was inserted into a TIMESTAMP WITH TIME ZONE column under the
Helsinki session timezone.  This produced shifts of 4 or 6 hours.

This script identifies affected rows and corrects datetime_utc to equal
datetime (interpreted as UTC).

Usage:
    mascope dev db script run fix_helsinki_datetime_utc
    mascope prod db script run fix_helsinki_datetime_utc

    # Only fix rows with datetime >= 2025-06-01 (skip legacy Helsinki data):

    # Linux / macOS:
    MIN_DATETIME=2025-06-01T00:00:00 mascope dev db script run fix_helsinki_datetime_utc

    # Windows PowerShell:
    $env:MIN_DATETIME="2025-06-01T00:00:00"; mascope dev db script run fix_helsinki_datetime_utc

    # For a client PC with a known UTC offset (e.g. +2h):
    UTC_OFFSET_HOURS=2 mascope dev db script run fix_helsinki_datetime_utc

    # Combine both:
    # Linux / macOS:
    MIN_DATETIME=2025-06-01T00:00:00 UTC_OFFSET_HOURS=2 mascope dev db script run fix_helsinki_datetime_utc

    # Windows PowerShell:
    $env:MIN_DATETIME="2025-06-01T00:00:00"; $env:UTC_OFFSET_HOURS="2"; mascope dev db script run fix_helsinki_datetime_utc

Date: 2026-04-28
"""

import asyncio
import os
from datetime import datetime

from mascope_backend.db import configure_database_engine
from mascope_backend.db.admin.fix_helsinki_datetime_utc import (
    fix_helsinki_datetime_utc,
)
from mascope_backend.runtime import runtime


# Rows with datetime before this cutoff are skipped.
# Set to None to process all rows, or to an ISO datetime string to skip
# legacy data where the Helsinki offset was intentional.
# Can be overridden via the MIN_DATETIME environment variable.
_MIN_DATETIME: str | None = None


async def run() -> None:
    """Initialize database and run the datetime_utc fix."""
    await configure_database_engine()

    min_dt = None
    env_val = os.environ.get("MIN_DATETIME")
    if env_val:
        min_dt = datetime.fromisoformat(env_val)
    elif _MIN_DATETIME is not None:
        min_dt = datetime.fromisoformat(_MIN_DATETIME)

    utc_offset_hours = int(os.environ.get("UTC_OFFSET_HOURS", "0"))

    result = await fix_helsinki_datetime_utc(
        min_datetime=min_dt,
        utc_offset_hours=utc_offset_hours,
    )

    runtime.logger.info("=" * 80)
    runtime.logger.info("FIX HELSINKI DATETIME_UTC COMPLETE")
    runtime.logger.info(f"Affected rows : {result['affected']}")
    runtime.logger.info(f"Updated rows  : {result['updated']}")
    runtime.logger.info("=" * 80)


def main() -> None:
    """Entry point for the Helsinki datetime fix script."""
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        runtime.logger.info("Cancelled by user (Ctrl+C)")
    except Exception:
        runtime.logger.exception("Script failed")
        raise


if __name__ == "__main__":
    main()
