"""
Remove cached sum signals.
"""

import asyncio
import os
import shutil

from mascope_backend.db import configure_database_engine
from mascope_backend.db.ops.backup import create_db_backup
from mascope_backend.db.ops.filestore import delete_sum_signal

from mascope_backend.runtime import runtime


async def run():
    # Step 1: Create backup before migration
    await create_db_backup()

    # Step 2: Setup new database version
    old_version = 35
    new_version = 36
    old_db_path = os.path.join(runtime.config.database, f"mascope.v{old_version}.db")
    new_db_path = os.path.join(runtime.config.database, f"mascope.v{new_version}.db")

    # Copy database file to new version
    shutil.copyfile(old_db_path, new_db_path)

    await configure_database_engine(new_version)
    runtime.logger.info(
        "Remove cached filtered sum signals, full sum signals will remain"
    )

    await delete_sum_signal(cached_only=True)

    runtime.logger.info(f"Migration to v{new_version} completed.")


if __name__ == "__main__":
    asyncio.run(run())
