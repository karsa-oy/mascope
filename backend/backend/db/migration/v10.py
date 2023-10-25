import os
import sqlite3
import shutil


def run():
    data_path = os.environ.get("MASCOPE_PRIVATE_DATADIR")

    # STEP 1 - setup new database
    old_db_path = os.path.join(data_path, "database", "mascope.v9.db")
    new_db_path = os.path.join(data_path, "database", "mascope.v10.db")
    shutil.copyfile(old_db_path, new_db_path)
    new_conn = sqlite3.connect(database=new_db_path)

    with new_conn:
        # STEP 2 - Add new field filter_params_ion to target_ion table
        print("Adding filter_params_ion field to target_ion table")
        new_conn.execute(
            """
            ALTER TABLE target_ion
            ADD COLUMN filter_params_ion JSON;
            """
        )

        # STEP 3 - Rename filter_params to filter_params_batch in sample_batch table
        print("Renaming filter_params to filter_params_batch in sample_batch table")

        # SQLite does not support the ALTER TABLE DROP COLUMN syntax.
        # To drop a column, you need to create a new table that has the same columns as the old table minus the column you want to drop.
        # Then, copy data from the old table to the new table.
        # And finally, you rename the new table to the old table.

        new_conn.execute(
            """
            CREATE TABLE sample_batch_new AS
            SELECT
                sample_batch_id,
                workspace_id,
                sample_batch_name,
                sample_batch_description,
                build_params,
                filter_params AS filter_params_batch,  -- Rename here
                sample_batch_utc_created,
                sample_batch_utc_modified
            FROM
                sample_batch;
            """
        )

        # Drop old table
        new_conn.execute("DROP TABLE sample_batch;")

        # Rename new table to old table
        new_conn.execute("ALTER TABLE sample_batch_new RENAME TO sample_batch;")

        new_conn.commit()
    new_conn.close()
