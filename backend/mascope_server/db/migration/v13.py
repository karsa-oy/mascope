import os
import shutil

from .lib.restore import run_db_restore
from .lib.maintenance import run_db_maintenance

def run():
    # Step 1: Setup new database
    data_path = os.environ.get("MASCOPE_PRIVATE_DATABASE_DIR")
    old_db_path = os.path.join(data_path, "mascope.v12.db")
    new_db_path = os.path.join(data_path, "mascope.v13.db")
    shutil.copyfile(old_db_path, new_db_path)

    # Step 2: Run db-restore
    # This will restore the database correct table schemas, create the missing indexes.
    # The configuration of table schemas is stored in the table_configs.
    run_db_restore()

    # Step 3: Run db-maintenance
    run_db_maintenance()
