import os
import asyncio
from sqlalchemy import text
from mascope_server.db import (
    get_available_db_version,
    get_current_db_version,
    configure_database_engine,
    async_session,
)
from mascope_server.db.ops.backup import create_db_backup

from mascope_server.runtime import runtime
from mascope_server.db.models import Base, Sample


async def create_database():
    last_version = get_available_db_version()
    existing_version = get_current_db_version()
    # Check if the last version matches the existing version
    if last_version == existing_version:
        runtime.logger.warning(
            f"Existing database with the last available version {existing_version} detected, creating a backup."
        )
        db_path = os.path.join(
            runtime.config.database, f"mascope.v{existing_version}.db"
        )
        if not os.path.exists(db_path):
            runtime.logger.error("Existing database file not found.")
            return

        # Create the backup
        await create_db_backup()

        # Remove the old database
        try:
            os.remove(db_path)
            runtime.logger.info(f"Removed previous database file: {db_path}")
        except PermissionError as e:
            runtime.logger.error(f"Failed to remove the database file: {e}")
            return
    # configure the database connection which will create a new database file (also updates the global async_session)
    configure_database_engine(last_version)

    # Create all tables in the database according to models defined in the Base
    async with async_session() as session:
        # Acquire a connection
        connection = await session.connection()

        # Explicitly create tables, excluding the Sample view
        for table_name, table_obj in Base.metadata.tables.items():
            if table_name != Sample.__tablename__:
                await connection.run_sync(table_obj.create)

        # Create the sample_view
        await connection.execute(
            text(
                """
            CREATE VIEW IF NOT EXISTS sample_view AS
            SELECT
                sample_item.sample_item_id,
                sample_file.sample_file_id,
                sample_file.instrument_function_id,
                sample_item.sample_batch_id,
                sample_item.sample_item_name,
                sample_file.filename,
                sample_file.instrument,
                sample_file.method_file,
                sample_item.sample_item_type,
                sample_item.sample_item_attributes,
                sample_item.filter_id,
                sample_file.length,
                sample_file.tic,
                sample_file.polarity,
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
        )
        await session.commit()

    runtime.logger.info(f"New database mascope.v{last_version} created successfully.")


def run():
    asyncio.run(create_database())


if __name__ == "__main__":
    run()
