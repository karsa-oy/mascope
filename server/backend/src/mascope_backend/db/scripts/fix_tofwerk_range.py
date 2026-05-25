"""
Maintenance script to fix corrupted m/z range values in sample_file records
and their corresponding filestore .props files.

A bug in H5Processor.range caused the full mass axis array to be stored
instead of [first, last]. This script:

1. Queries the database for sample_file rows where range has > 2 elements.
2. Fixes the database rows to [first, last].
3. Uses the affected filenames to locate and patch the .props files.

Usage:
    mascope dev db script run fix_tofwerk_range
    mascope prod db script run fix_tofwerk_range

Date: 2026-05-25
"""

import asyncio

from mascope_backend.db import configure_database_engine
from mascope_backend.db.admin.fix_tofwerk_range import fix_tofwerk_range
from mascope_backend.runtime import runtime


async def run() -> None:
    """Initialize database and run the range fix."""
    await configure_database_engine()

    result = await fix_tofwerk_range()

    db = result["database"]
    fs = result["filestore"]

    runtime.logger.info("=" * 80)
    runtime.logger.info("FIX TOFWERK RANGE COMPLETE")
    runtime.logger.info(
        f"Database — affected: {db['affected']}, updated: {db['updated']}"
    )
    runtime.logger.info(
        f"Filestore — checked: {fs['checked']}, updated: {fs['updated']}, "
        f"missing: {fs['missing']}, errors: {len(fs['errors'])}"
    )
    runtime.logger.info("=" * 80)


def main() -> None:
    """Entry point for the TofWerk range fix script."""
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        runtime.logger.info("Cancelled by user (Ctrl+C)")
    except Exception:
        runtime.logger.exception("Script failed")
        raise


if __name__ == "__main__":
    main()
