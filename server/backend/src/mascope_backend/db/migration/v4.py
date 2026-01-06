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
    old_db_path = os.path.join(runtime.config.database, "mascope.v3.db")
    new_db_path = os.path.join(runtime.config.database, "mascope.v4.db")
    shutil.copyfile(old_db_path, new_db_path)
    new_conn = sqlite3.connect(database=new_db_path)
    with new_conn:
        # Create match interference table
        new_conn.execute(
            """--sql
            CREATE TABLE match_interference (
                match_interference_id VARCHAR(32) PRIMARY KEY
                ,target_isotope_id VARCHAR(32) NOT NULL
                    REFERENCES target_isotope(target_isotope_id)
                ,sample_item_id VARCHAR(16) NOT NULL
                        REFERENCES sample_item(sample_item_id)
                ,sample_peak_interference FLOAT NOT NULL
            );
        """
        )
        new_conn.commit()
    new_conn.close()
