import nest_asyncio
import os
import pandas as pd
import sqlite3
import shutil

from backend.db.conn import conn
from backend.lib.file import filename_to_zarr_path

# patch asyncio to supported run_until_complete
# when an event loop is already running
nest_asyncio.apply()


def run():
    data_path = os.environ.get('MASCOPE_PRIVATE_DATADIR')

    # STEP 1 - setup new database
    old_db_path = os.path.join(data_path, 'database', 'mascope.v4.db')
    new_db_path = os.path.join(data_path, 'database', 'mascope.v5.db')
    shutil.copyfile(old_db_path, new_db_path)
    new_conn = sqlite3.connect(database=new_db_path)
    with new_conn:
        # Delete sample file records without file
        filenames = pd.read_sql("""--sql
            SELECT
                filename
            FROM sample_file
            """,
            new_conn
        ).filename.tolist()

        # Delete all peak datasets
        for filename in filenames:
            peaks_path = filename_to_zarr_path(filename, 'peaks')
            try:
                shutil.rmtree(peaks_path)
            except Exception as e:
                print(e)

        # Delete all matches
        new_conn.cursor().execute(f"""--sql
            DELETE FROM match
        """)
        new_conn.cursor().execute(f"""--sql
            ALTER TABLE match
            RENAME COLUMN sample_peak_height TO sample_peak_area;
        """)
        new_conn.cursor().execute(f"""--sql
            ALTER TABLE match
            RENAME COLUMN sample_peak_height_relative TO sample_peak_area_relative;
        """)
        new_conn.commit()
    new_conn.close()