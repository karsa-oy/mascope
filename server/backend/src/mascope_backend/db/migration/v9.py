import nest_asyncio
import os
import sqlite3
import shutil


from mascope_backend.runtime import runtime

# patch asyncio to support run_until_complete
# when an event loop is already running
nest_asyncio.apply()


def run():
    # STEP 1 - setup new database
    old_db_path = os.path.join(runtime.config.database, "mascope.v8.db")
    new_db_path = os.path.join(runtime.config.database, "mascope.v9.db")
    shutil.copyfile(old_db_path, new_db_path)
    new_conn = sqlite3.connect(database=new_db_path)

    with new_conn:
        runtime.logger.info("Creating match_rating table")
        # Create match_rating table
        new_conn.execute(
            """
            CREATE TABLE match_rating (
                match_rating_id VARCHAR(32) PRIMARY KEY,
                sample_item_id VARCHAR(16) NOT NULL
                    REFERENCES sample_item(sample_item_id) ON DELETE CASCADE,
                target_ion_id VARCHAR(32) NOT NULL
                    REFERENCES target_ion(target_ion_id) ON DELETE CASCADE,
                match_rating_utc_created TIMESTAMP NOT NULL,
                rating INTEGER CHECK (rating BETWEEN 0 AND 2) NOT NULL,
                checklist JSON,
                environment JSON
            );
            """
        )

        new_conn.commit()
    new_conn.close()
