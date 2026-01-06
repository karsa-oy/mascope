import asyncio
import os
import shutil

from mascope_backend.db import configure_database_engine
from mascope_backend.db.ops.maintenance import db_maintenance
from mascope_backend.db.ops.restore import db_restore
from mascope_backend.runtime import runtime


async def run():
    # Step 1: Setup new database
    new_version = 13
    old_db_path = os.path.join(runtime.config.database, "mascope.v12.db")
    new_db_path = os.path.join(runtime.config.database, f"mascope.v{new_version}.db")
    shutil.copyfile(old_db_path, new_db_path)

    # Update the engine to the new database (also updates global async_session)
    configure_database_engine(new_version)

    # Step 2: Run db-restore (async)
    # This will restore the correct table schemas and create missing indexes.
    await db_restore()

    # Step 3: Run db-maintenance (async)
    await db_maintenance()


if __name__ == "__main__":
    asyncio.run(run())
