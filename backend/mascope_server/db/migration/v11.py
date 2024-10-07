import os
import sqlite3
import shutil

from mascope_server.runtime import runtime


def run():
    # STEP 1 - setup new database
    old_db_path = os.path.join(runtime.config.database, "mascope.v10.db")
    new_db_path = os.path.join(runtime.config.database, "mascope.v11.db")
    shutil.copyfile(old_db_path, new_db_path)
    new_conn = sqlite3.connect(database=new_db_path)

    with new_conn:
        # STEP 1: Rename sample type HOT -> SAMPLE
        new_conn.execute(
            """
            UPDATE sample_item
                SET sample_item_type = 'SAMPLE'
                WHERE sample_item_type = 'HOT'   
            """
        )
        # STEP 2: Split sample type BACKGROUND into INSTRUMENT_BACKGROUND and FILTER_BACKGROUND
        new_conn.execute(
            """
            UPDATE sample_item
                SET sample_item_type = 'INSTRUMENT_BACKGROUND'
                WHERE sample_item_type = 'BACKGROUND'
                AND filter_id IS NULL
            """
        )
        new_conn.execute(
            """
            UPDATE sample_item
                SET sample_item_type = 'FILTER_BACKGROUND'
                WHERE sample_item_type = 'BACKGROUND'
                AND filter_id IS NOT NULL
            """
        )

    new_conn.close()
