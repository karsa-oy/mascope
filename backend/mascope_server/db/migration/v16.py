import os
import shutil
import asyncio
from sqlalchemy import text
from mascope_server.db import async_session, configure_database_engine
from mascope_server.db.models import InstrumentFunction, SampleFile
from mascope_server.db.ops.backup import create_db_backup
from mascope_server.db.ops.restore import db_restore
from mascope_server.db.ops.maintenance import db_maintenance
from mascope_server.runtime import runtime


async def run():
    """
    Asynchronous migration script for v16.
    - Creates a backup of the databas and sets up a new database.
    - Restores the updated table schema for ionization_mechanism.
    - Applies schema updates to `instrument_function` and `sample_file`.
    - Updates the `sample_view` to reflect the new fields.
    - Runs maintenance on the updated database.
    """
    await create_db_backup()

    # Step 1: Setup new database version
    new_version = 16
    old_db_path = os.path.join(runtime.config.database, "mascope.v15.db")
    new_db_path = os.path.join(runtime.config.database, f"mascope.v{new_version}.db")
    shutil.copyfile(old_db_path, new_db_path)

    # Reconfigure the database engine to point to the new v16 database
    await configure_database_engine(new_version)

    # Step 2: Restore the schema of the ionization_mechanism table with its
    # updated definition (nullable reagent, unique constraint)
    runtime.logger.info("Updating ionization_mechanism table schema.")
    await db_restore(tables_to_restore=["ionization_mechanism"])

    # Step 3: Update instrument_function table (add method_file, not nullable datetime_utc)
    await modify_instrument_function_schema()

    # Step 4: Update sample_file schema with method_file and instrument_function_id
    await modify_sample_file_schema()

    # Step 5: Update the Sample view to reflect new columns
    await update_sample_view()

    # Step 6: Run database maintenance (vacuum, analyze, integrity check)
    await db_maintenance()


if __name__ == "__main__":
    asyncio.run(run())


async def modify_instrument_function_schema():
    """
    Adds `method_file` column to instrument_function, making it non-nullable,
    `datetime_utc` becomes  non-nullable.
    Populates method_file based on `datetime_utc` using `YYYYMMDD` format.
    """
    async with async_session() as session:
        runtime.logger.info(
            "Adding the method_file column to instrument_function table schema."
        )
        # Step 1: Create a temporary backup table and copy data into it
        await session.execute(
            text(
                """
            CREATE TABLE instrument_function_backup AS
            SELECT * FROM instrument_function;
        """
            )
        )

        # Step 2: Drop the original table
        await session.execute(text("DROP TABLE instrument_function;"))

        # Step 3: Create the new table using the InstrumentFunction model schema
        connection = await session.connection()
        await connection.run_sync(InstrumentFunction.__table__.create)

        # Step 4: Repopulate data, setting `method_file` based on `datetime_utc`
        await session.execute(
            text(
                """
            INSERT INTO instrument_function (
                instrument_function_id, instrument, method_file, datetime_utc, peakshape, resolution_function
            )
            SELECT 
                instrument_function_id, 
                instrument,
                COALESCE(strftime('%Y%m%d', datetime_utc), '00000000'),  -- Format datetime_utc or fallback to '00000000'
                datetime_utc, 
                peakshape, 
                resolution_function
            FROM instrument_function_backup;
        """
            )
        )

        # Step 5: Drop the backup table
        await session.execute(text("DROP TABLE instrument_function_backup;"))

        await session.commit()


async def modify_sample_file_schema():
    """
    Adds the `instrument_function_id` and `method_file` columns to `sample_file`.
    """
    async with async_session() as session:
        runtime.logger.info(
            "Adding instrument_function_id and method_file to sample_file table."
        )

        # Step 1: Create a temporary backup table and copy data
        await session.execute(
            text(
                """
                CREATE TABLE sample_file_backup AS
                SELECT * FROM sample_file;
            """
            )
        )

        # Step 2: Drop the original table
        await session.execute(text("DROP TABLE sample_file;"))

        # Step 3: Recreate the table using SQLAlchemy model
        connection = await session.connection()
        await connection.run_sync(SampleFile.__table__.create)

        # Step 4: Repopulate data from the backup table
        await session.execute(
            text(
                """
                INSERT INTO sample_file (
                    sample_file_id, filename, instrument, datetime, datetime_utc,
                    length, range, mz_calibration, tic, polarity
                )
                SELECT
                    sample_file_id, filename, instrument, datetime, datetime_utc,
                    length, range, mz_calibration, tic, polarity
                FROM sample_file_backup;
            """
            )
        )

        # Step 5: Drop the backup table
        await session.execute(text("DROP TABLE sample_file_backup;"))

        await session.commit()


async def update_sample_view():
    """
    Updates the sample_view to include method_file and instrument_function_id fields.
    """
    async with async_session() as session:
        runtime.logger.info("Updating sample_view to include new fields.")

        # Step 1: Drop the old view
        await session.execute(text("DROP VIEW IF EXISTS sample_view"))

        # Step 2: Recreate the view with updated columns
        await session.execute(
            text(
                """
                CREATE VIEW sample_view AS
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
