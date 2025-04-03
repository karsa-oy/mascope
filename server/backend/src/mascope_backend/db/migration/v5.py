import nest_asyncio
import os
import pandas as pd
import sqlite3
import shutil

from mascope_file.name import filename_to_zarr_path


from mascope_backend.runtime import runtime

# patch asyncio to supported run_until_complete
# when an event loop is already running
nest_asyncio.apply()


def run():
    # STEP 1 - setup new database
    old_db_path = os.path.join(runtime.config.database, "mascope.v4.db")
    new_db_path = os.path.join(runtime.config.database, "mascope.v5.db")
    shutil.copyfile(old_db_path, new_db_path)
    new_conn = sqlite3.connect(database=new_db_path)
    with new_conn:
        # Delete sample file records without file
        filenames = pd.read_sql(
            """--sql
            SELECT
                filename
            FROM sample_file
            """,
            new_conn,
        ).filename.tolist()

        # Delete all peak datasets
        for filename in filenames:
            peaks_path = filename_to_zarr_path(filename, "peaks")
            try:
                shutil.rmtree(peaks_path)
            except Exception as e:
                runtime.logger.error(e)
        # Delete all matches
        new_conn.cursor().execute(
            f"""--sql
            DELETE FROM match
        """
        )
        new_conn.cursor().execute(
            f"""--sql
            ALTER TABLE match
            RENAME COLUMN sample_peak_height TO sample_peak_area;
        """
        )
        new_conn.cursor().execute(
            f"""--sql
            ALTER TABLE match
            RENAME COLUMN sample_peak_height_relative TO sample_peak_area_relative;
        """
        )
        # Redo match interferences table
        new_conn.cursor().execute(
            f"""--sql
            DROP TABLE match_interference
        """
        )
        new_conn.execute(
            """--sql
            CREATE TABLE match_interference (
                match_interference_id VARCHAR(32) PRIMARY KEY
                ,target_isotope_id VARCHAR(32) NOT NULL
                    REFERENCES target_isotope(target_isotope_id)
                    ON DELETE CASCADE
                ,sample_item_id VARCHAR(16) NOT NULL
                    REFERENCES sample_item(sample_item_id)
                    ON DELETE CASCADE
                ,sample_peak_interference FLOAT NOT NULL
            );
        """
        )
        new_conn.commit()
    new_conn.close()
