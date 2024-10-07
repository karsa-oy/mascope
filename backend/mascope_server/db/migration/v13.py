import os
import shutil

from mascope_server.db.ops.restore import run_db_restore
from mascope_server.db.ops.maintenance import run_db_maintenance

from mascope_server.runtime import runtime


def run():
    # Step 1: Setup new database
    old_db_path = os.path.join(runtime.config.database, "mascope.v12.db")
    new_db_path = os.path.join(runtime.config.database, "mascope.v13.db")
    shutil.copyfile(old_db_path, new_db_path)

    # Step 2: Run db-restore
    # This will restore the database correct table schemas, create the missing indexes.
    # The configuration of table schemas is stored in the table_configs.
    run_db_restore()

    # Step 3: Run db-maintenance
    run_db_maintenance()
