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
    old_db_path = os.path.join(runtime.config.database, "mascope.v7.db")
    new_db_path = os.path.join(runtime.config.database, "mascope.v8.db")
    shutil.copyfile(old_db_path, new_db_path)
    new_conn = sqlite3.connect(database=new_db_path)
    with new_conn:
        runtime.logger.info("Create view sample_view")
        new_conn.execute(
            """
            CREATE VIEW sample_view AS
            SELECT
                sample_item.sample_item_id,
                sample_file.sample_file_id,
                sample_item.sample_batch_id,
                sample_item.sample_item_name,
                sample_file.instrument,
                sample_item.filename,
                sample_item.sample_item_type,
                sample_item.sample_item_attributes,
                sample_item.filter_id,
                sample_file.length,
                sample_file.tic,
                sample_file.range,
                sample_file.mz_calibration,
                sample_file.datetime,
                sample_file.datetime_utc,
                sample_item.sample_item_utc_created,
                sample_item.sample_item_utc_modified
            FROM
                sample_item
            JOIN
                sample_file ON sample_item.filename = sample_file.filename
            """
        )

        new_conn.commit()
    new_conn.close()
