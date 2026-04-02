import os
import shutil
import sqlite3

import nest_asyncio

from mascope_backend.runtime import runtime


# patch asyncio to supported run_until_complete
# when an event loop is already running
nest_asyncio.apply()


def run():
    # STEP 1 - setup new database
    old_db_path = os.path.join(runtime.config.database, "mascope.v5.db")
    new_db_path = os.path.join(runtime.config.database, "mascope.v6.db")
    shutil.copyfile(old_db_path, new_db_path)
    new_conn = sqlite3.connect(database=new_db_path)
    with new_conn:
        new_conn.cursor().execute(
            """--sql
            ALTER TABLE sample_item
            ADD filter_id VARCHAR(6)
        """
        )
