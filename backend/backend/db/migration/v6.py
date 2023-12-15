import nest_asyncio
import os
import sqlite3
import shutil

# patch asyncio to supported run_until_complete
# when an event loop is already running
nest_asyncio.apply()


def run():
    data_path = os.environ.get("MASCOPE_PRIVATE_DATABASE_DIR")

    # STEP 1 - setup new database
    old_db_path = os.path.join(data_path, "mascope.v5.db")
    new_db_path = os.path.join(data_path, "mascope.v6.db")
    shutil.copyfile(old_db_path, new_db_path)
    new_conn = sqlite3.connect(database=new_db_path)
    with new_conn:
        new_conn.cursor().execute(
            f"""--sql
            ALTER TABLE sample_item
            ADD filter_id VARCHAR(6)
        """
        )
