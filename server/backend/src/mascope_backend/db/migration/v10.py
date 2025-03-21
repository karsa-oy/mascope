import os
import sqlite3
import shutil


from mascope_backend.runtime import runtime


def run():
    # STEP 1 - setup new database
    old_db_path = os.path.join(runtime.config.database, "mascope.v9.db")
    new_db_path = os.path.join(runtime.config.database, "mascope.v10.db")
    shutil.copyfile(old_db_path, new_db_path)
    new_conn = sqlite3.connect(database=new_db_path)

    with new_conn:
        # STEP 2 - Add new field filter_params to target_ion table
        runtime.logger.info("Adding filter_params field to target_ion table")
        new_conn.execute(
            """
            ALTER TABLE target_ion
            ADD COLUMN filter_params JSON NOT NULL DEFAULT '{}';
            """
        )

        # STEP 3 - Drop filter_params field from sample_batch table
        runtime.logger.info("Dropping filter_params field from sample_batch table")
        new_conn.execute(
            "CREATE TABLE sample_batch_backup AS SELECT * FROM sample_batch;"
        )
        # Drop old table
        new_conn.execute("DROP TABLE sample_batch;")
        # Create new table with new structure
        new_conn.execute(
            """
            CREATE TABLE sample_batch (
                sample_batch_id VARCHAR(16) PRIMARY KEY,
                workspace_id VARCHAR(16) NOT NULL REFERENCES workspace(workspace_id) ON DELETE CASCADE,
                sample_batch_name VARCHAR NOT NULL,
                sample_batch_description TEXT,
                build_params JSON,
                sample_batch_utc_created TIMESTAMP,
                sample_batch_utc_modified TIMESTAMP
            );
            """
        )
        # Copy data from backup table to new table
        new_conn.execute(
            """
            INSERT INTO sample_batch (sample_batch_id, workspace_id, sample_batch_name, sample_batch_description, build_params, sample_batch_utc_created, sample_batch_utc_modified)
            SELECT sample_batch_id, workspace_id, sample_batch_name, sample_batch_description, build_params, sample_batch_utc_created, sample_batch_utc_modified FROM sample_batch_backup;
            """
        )
        # Drop backup table
        new_conn.execute("DROP TABLE sample_batch_backup;")

        # STEP 4 - Add new field target_collection_type to target_collection table
        runtime.logger.info(
            "Adding target_collection_type field to target_collection table"
        )
        new_conn.execute(
            """
            ALTER TABLE target_collection
            ADD COLUMN target_collection_type VARCHAR(64) NOT NULL DEFAULT 'TARGETS';
            """
        )

        new_conn.commit()
    new_conn.close()
