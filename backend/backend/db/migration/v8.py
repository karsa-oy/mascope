import nest_asyncio
import os
import pandas as pd
import sqlite3
import shutil
from backend.db.id import gen_id

# patch asyncio to supported run_until_complete
# when an event loop is already running
nest_asyncio.apply()


def run():
    data_path = os.environ.get("MASCOPE_PRIVATE_DATADIR")

    # STEP 1 - setup new database
    old_db_path = os.path.join(data_path, "database", "mascope.v7.db")
    new_db_path = os.path.join(data_path, "database", "mascope.v8.db")
    shutil.copyfile(old_db_path, new_db_path)
    new_conn = sqlite3.connect(database=new_db_path)
    with new_conn:
        # Create new sample table
        print("Create table sample")
        new_conn.execute(
            """--sql
            CREATE TABLE sample (
                sample_id VARCHAR(16) NOT NULL PRIMARY KEY,
                sample_item_id VARCHAR(16) NOT NULL,
                sample_file_id VARCHAR(256) NOT NULL,
                sample_batch_id VARCHAR(16) NOT NULL,
                sample_item_name VARCHAR(256) NOT NULL,
                filename VARCHAR(256) NOT NULL,
                instrument VARCHAR(64),
                sample_item_type VARCHAR(64) NOT NULL,
                sample_item_attributes VARCHAR,
                filter_id VARCHAR(6),
                length FLOAT,
                range JSON,
                mz_calibration JSON,
                tic,
                datetime TIMESTAMP WITH TIME ZONE,
                datetime_utc TIMESTAMP,
                sample_item_utc_created TIMESTAMP,
                sample_item_utc_modified TIMESTAMP
            );
        """
        )

        # STEP 2 - load old tables into pandas dataframes and write to new sample table
        sample_item_df = pd.read_sql("SELECT * FROM sample_item", new_conn)
        sample_file_df = pd.read_sql("SELECT * FROM sample_file", new_conn)

        # Merge the dataframes on filename
        merged_df = pd.merge(sample_item_df, sample_file_df, on="filename")

        # Generate new sample_id for each row in the dataframe
        merged_df["sample_id"] = [gen_id() for _ in range(len(merged_df))]

        # Select the necessary columns for the new table
        sample_df = merged_df[
            [
                "sample_id",
                "sample_item_id",
                "sample_file_id",
                "sample_batch_id",
                "sample_item_name",
                "filename",
                "instrument",
                "sample_item_type",
                "sample_item_attributes",
                "filter_id",
                "length",
                "range",
                "mz_calibration",
                "tic",
                "datetime",
                "datetime_utc",
                "sample_item_utc_created",
                "sample_item_utc_modified",
            ]
        ]

        # Write data to new sample table
        sample_df.to_sql("sample", new_conn, if_exists="append", index=False)

        new_conn.commit()
    new_conn.close()
