import os
import shutil
import asyncio
from sqlalchemy import text, select

from mascope_server.api.controllers.match.match_aggregate_controller import (
    aggregate_and_create_matches,
)
from mascope_server.api.models.models import SampleBatch

from mascope_server.config import config

from mascope_server.db import configure_database_engine, async_session

import mascope_runtime as runtime

logger = runtime.logger.service('backend')

async def run():
    # Step 1: Setup new database
    new_version = 14
    # Define the database paths
    old_db_path = os.path.join(config.server.database, "mascope.v13.db")
    new_db_path = os.path.join(config.server.database, f"mascope.v{new_version}.db")
    shutil.copyfile(old_db_path, new_db_path)  # Copy new version for migration

    # Update the engine to the new database (should update the global async_session, so no restart needed)
    configure_database_engine(new_version)

    # Step 2: Rename match table to match_isotope
    logger.info("Renaming match table to match_isotope.")
    async with async_session() as session:  # Perform database operations using async_session
        # Create backup of the current match table
        await session.execute(text("CREATE TABLE match_backup AS SELECT * FROM match;"))
        # Drop the old match table
        await session.execute(text("DROP TABLE match;"))

        # Create the new match_isotope table with updated schema
        await session.execute(
            text(
                """
            CREATE TABLE match_isotope (
                match_isotope_id VARCHAR(32) NOT NULL PRIMARY KEY,
                target_isotope_id VARCHAR(16) NOT NULL
                    REFERENCES target_isotope(target_isotope_id) ON DELETE CASCADE,
                sample_item_id VARCHAR(16) NOT NULL
                    REFERENCES sample_item(sample_item_id) ON DELETE CASCADE,
                sample_peak_id INT NOT NULL,
                sample_peak_mz FLOAT NOT NULL,
                sample_peak_area FLOAT NOT NULL,
                sample_peak_area_relative FLOAT NOT NULL,
                sample_peak_tof FLOAT NOT NULL,
                match_abundance_error FLOAT NOT NULL,
                match_mz_error FLOAT NOT NULL,
                match_isotope_correlation FLOAT NOT NULL,
                match_score FLOAT NOT NULL
                    CHECK (match_score BETWEEN 0 AND 1),
                match_isotope_utc_created TIMESTAMP,
                match_isotope_utc_modified TIMESTAMP
            );
        """
            )
        )

        # Copy data from backup table to the new match_isotope table
        await session.execute(
            text(
                """
            INSERT INTO match_isotope (
                match_isotope_id, target_isotope_id, sample_item_id, sample_peak_id,
                sample_peak_mz, sample_peak_area, sample_peak_area_relative, sample_peak_tof,
                match_abundance_error, match_mz_error, match_isotope_correlation, match_score, 
                match_isotope_utc_created, match_isotope_utc_modified
            )
            SELECT 
                match_id, target_isotope_id, sample_item_id, sample_peak_id,
                sample_peak_mz, sample_peak_area, sample_peak_area_relative, sample_peak_tof,
                match_abundance_error, match_mz_error, match_isotope_correlation, match_score, NULL, NULL
            FROM match_backup;
        """
            )
        )

        # Drop the backup table
        await session.execute(text("DROP TABLE match_backup;"))

        # Create indexes if needed
        await session.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_match_isotope_sample_item ON match_isotope (sample_item_id);"
            )
        )

        # Commit the transaction
        await session.commit()

    #  Step 3: Create new match_ tables
    logger.info("Creating new match_ tables.")
    async with async_session() as session:  # Perform database operations using async_session
        # Create match_sample table
        await session.execute(
            text(
                """
            CREATE TABLE match_sample (
                match_sample_id VARCHAR(32) NOT NULL PRIMARY KEY,
                sample_item_id VARCHAR(16) NOT NULL
                    REFERENCES sample_item(sample_item_id) ON DELETE CASCADE,
                match_score FLOAT NOT NULL
                    CHECK (match_score BETWEEN 0 AND 1),
                match_category INTEGER NOT NULL
                    CHECK (match_category BETWEEN 0 AND 2),
                sample_peak_area_sum FLOAT NOT NULL,
                sample_peak_interference_sum FLOAT NOT NULL,
                match_sample_utc_created TIMESTAMP,
                match_sample_utc_modified TIMESTAMP
            );
            """
            )
        )
        # Create match_collection table
        await session.execute(
            text(
                """
            CREATE TABLE match_collection (
                match_collection_id VARCHAR(32) NOT NULL PRIMARY KEY,
                sample_item_id VARCHAR(16) NOT NULL
                    REFERENCES sample_item(sample_item_id) ON DELETE CASCADE,
                target_collection_id VARCHAR(16) NOT NULL
                    REFERENCES target_collection(target_collection_id) ON DELETE CASCADE,
                match_score FLOAT NOT NULL
                    CHECK (match_score BETWEEN 0 AND 1),
                match_category INTEGER NOT NULL
                    CHECK (match_category BETWEEN 0 AND 2),
                sample_peak_area_sum FLOAT NOT NULL,
                sample_peak_interference_sum FLOAT NOT NULL,
                match_collection_utc_created TIMESTAMP,
                match_collection_utc_modified TIMESTAMP
            );
            """
            )
        )
        # Create match_compound table
        await session.execute(
            text(
                """
            CREATE TABLE match_compound (
                match_compound_id VARCHAR(32) NOT NULL PRIMARY KEY,
                sample_item_id VARCHAR(16) NOT NULL
                    REFERENCES sample_item(sample_item_id) ON DELETE CASCADE,
                target_compound_id VARCHAR(16) NOT NULL
                    REFERENCES target_compound(target_compound_id) ON DELETE CASCADE,
                match_score FLOAT NOT NULL
                    CHECK (match_score BETWEEN 0 AND 1),
                match_category INTEGER NOT NULL
                    CHECK (match_category BETWEEN 0 AND 2),
                sample_peak_area_sum FLOAT NOT NULL,
                sample_peak_interference_sum FLOAT NOT NULL,
                match_compound_utc_created TIMESTAMP,
                match_compound_utc_modified TIMESTAMP
            );
            """
            )
        )

        # Create match_ion table
        await session.execute(
            text(
                """
            CREATE TABLE match_ion (
                match_ion_id VARCHAR(32) NOT NULL PRIMARY KEY,
                sample_item_id VARCHAR(16) NOT NULL
                    REFERENCES sample_item(sample_item_id) ON DELETE CASCADE,
                target_ion_id VARCHAR(16) NOT NULL
                    REFERENCES target_ion(target_ion_id) ON DELETE CASCADE,
                match_score FLOAT NOT NULL
                    CHECK (match_score BETWEEN 0 AND 1),
                match_category INTEGER NOT NULL
                    CHECK (match_category BETWEEN 0 AND 2),
                sample_peak_area_sum FLOAT NOT NULL,
                sample_peak_interference_sum FLOAT NOT NULL,
                match_ion_utc_created TIMESTAMP,
                match_ion_utc_modified TIMESTAMP
            );
        """
            )
        )

        # Commit the transaction
        await session.commit()

    # Step 4: Aggregate and create matches for all sample batches
    async with async_session() as session:
        stmt = select(SampleBatch)
        result = await session.execute(stmt)
        sample_batches = result.scalars().all()

    total_batches = len(sample_batches)
    logger.info(f"Aggregating and creating matches for {total_batches} sample batches.")

    # Call the aggregate_and_create_matches for each batch
    for index, batch in enumerate(sample_batches, start=1):
        try:
            logger.info(
                f"Processing batch {index}/{total_batches}: {batch.sample_batch_name}"
            )
            await aggregate_and_create_matches(sample_batch_id=batch.sample_batch_id)
        except Exception as e:
            logger.error(
                f"Failed to aggregating and create matches for sample batch '{batch.sample_batch_name}': {str(e)}"
            )

    logger.info(f"Migration to v{new_version} completed successfully.")


if __name__ == "__main__":
    asyncio.run(run())
