import os
import sys
import sqlite3
import asyncio

from mascope_server.db import get_current_db_version
from mascope_server.db.ops.backup import create_db_backup
from mascope_server.db.tables_config import get_table_configs

from mascope_server.runtime import runtime


# -----------------------------
# Async entry point for restoration
# -----------------------------


async def db_restore(tables_to_restore=None):
    """
    Asynchronously orchestrates the schema restoration process for specified database tables.
    If `tables_to_restore` is None, all tables will be restored.

    1. Backs up the current database.
    2. Validates that all specified tables have configurations.
    3. Restores the schema for each table to ensure it matches the expected configuration.
    4. Deletes any orphaned records that do not comply with foreign key constraints.
    5. Creates necessary indexes if they do not exist.

    Uses separate database connections for each major step to ensure changes are applied correctly and
    to manage database transactions effectively.

    :param tables_to_restore: List of tables to restore, defaults to restoring all tables.
    """
    await create_db_backup()

    # Determine the current version and paths
    data_path = runtime.config.database
    current_version = get_current_db_version()
    db_path = os.path.join(data_path, f"mascope.v{current_version}.db")

    # Get table configs for current version or most recent config
    table_configs = get_table_configs()

    # Default to all tables if no specific tables are provided
    if tables_to_restore is None:
        tables_to_restore = list(table_configs.keys())

    # Step 2: Validate that all specified tables have configurations
    for table_name in tables_to_restore:
        if table_name not in table_configs:
            runtime.logger.error(
                f"No configuration found for '{table_name}'. Please check your table name or define its configuration."
            )
            return  # Exit the function if a table configuration is missing

    # Step 3: Restore the schema of each table
    loop = asyncio.get_running_loop()  # Get the current event loop
    for table_name in tables_to_restore:
        await loop.run_in_executor(
            None, restore_table_sync, db_path, table_name, table_configs[table_name]
        )

    # Step 4: Delete orphaned records after restoring schema
    runtime.logger.info("Checking for orphaned records...")
    for table_name in tables_to_restore:
        await loop.run_in_executor(
            None, delete_orphaned_records_sync, db_path, table_name
        )

    # Step 5: Create indexes after restoring schema and cleaning up orphans
    runtime.logger.info("Checking for missing indexes...")
    for table_name in tables_to_restore:
        await loop.run_in_executor(
            None, create_indexes_sync, db_path, table_name, table_configs[table_name]
        )


# -----------------------------
# CLI entry point for synchronous execution
# -----------------------------


def run_db_restore():
    """
    Orchestrates the schema restoration process for specified database tables in synchronous mode.
    This function wraps the async restore function using asyncio.run.
    """
    # Extract table names from CLI arguments or restore all tables
    tables_to_restore = sys.argv[1:] if len(sys.argv) > 1 else None

    # Run the async function in a sync environment
    asyncio.run(db_restore(tables_to_restore))


# -----------------------------
# Sync to async helper functions
# -----------------------------


def restore_table_sync(db_path, table_name, schema_info):
    """
    Synchronously restore a table schema.
    """
    with sqlite3.connect(db_path) as conn:
        restore_table(conn, table_name, schema_info)
        conn.commit()


def delete_orphaned_records_sync(db_path, table_name):
    """
    Synchronously delete orphaned records based on foreign key constraints.
    """
    with sqlite3.connect(db_path) as conn:
        delete_orphaned_records(conn, table_name)
        conn.commit()


def create_indexes_sync(db_path, table_name, schema_info):
    """
    Synchronously create indexes.
    """
    with sqlite3.connect(db_path) as conn:
        create_indexes(conn, table_name, schema_info)
        conn.commit()


# -----------------------------
# Utility functions for database operations
# -----------------------------


def create_table_backup(cursor, table_name):
    """
    Creates a backup of the specified table within the same database with copied data.
    """
    cursor.execute(f"CREATE TABLE {table_name}_backup AS SELECT * FROM {table_name};")


def update_backup_table(cursor, table_name):
    """
    Updates the backup table, specifically used for 'sample_batch' to handle NULL workspace IDs.

    :param cursor: The database cursor to execute the query.
    :param table_name: Name of the table, currently affects only 'sample_batch'.
    """
    if table_name == "sample_batch":
        # Insert a temporary workspace_id for NULL ids
        cursor.execute(
            """
            UPDATE sample_batch_backup
            SET workspace_id = '_DELETE'
            WHERE workspace_id IS NULL;
        """
        )


def drop_table(cursor, table_name):
    """
    Drops the specified table from the database.
    """
    cursor.execute(f"DROP TABLE {table_name};")


def restore_data_from_backup(cursor, table_name, columns):
    """
    Restores data from a backup table to the main table using the specified columns.

    :param cursor: The database cursor to execute the query.
    :param table_name: Name of the table to restore data to.
    :param columns: List of columns to include during data restoration.
    """
    column_list = ", ".join(columns)
    cursor.execute(
        f"""
        INSERT INTO {table_name} ({column_list})
        SELECT {column_list} FROM {table_name}_backup;
    """
    )
    # Remove backup table after restoring data
    cursor.execute(f"DROP TABLE {table_name}_backup;")


def delete_orphaned_records(conn, table_name):
    """
    Deletes orphaned records from specified tables based on foreign key constraints.

    :param conn: Database connection object.
    :param table_name: Name of the table to check and delete orphaned records.
    """
    cursor = conn.cursor()
    # Enable foreign key constraint enforcement to ensure cascade deletes
    cursor.execute("PRAGMA foreign_keys = ON;")
    if table_name == "sample_batch":
        cursor.execute(
            """
            DELETE FROM sample_batch 
            WHERE workspace_id = '_DELETE' OR workspace_id NOT IN (SELECT workspace_id FROM workspace);
        """
        )
        deleted_count = cursor.rowcount
        if deleted_count > 0:
            runtime.logger.info(
                f"🗑️ Deleted {deleted_count} orphaned sample_batch records due to invalid workspace_id."
            )
    elif table_name == "target_compound_in_target_collection":
        cursor.execute(
            """
            DELETE FROM target_compound_in_target_collection 
            WHERE target_compound_id NOT IN (SELECT target_compound_id FROM target_compound);
        """
        )
        deleted_count = cursor.rowcount
        if deleted_count > 0:
            runtime.logger.info(
                f"🗑️ Deleted {deleted_count} orphaned target_compound_in_target_collection records due to invalid target_compound_id."
            )

    elif table_name == "target_collection_in_sample_batch":
        cursor.execute(
            """
            DELETE FROM target_collection_in_sample_batch 
            WHERE sample_batch_id NOT IN (SELECT sample_batch_id FROM sample_batch);
        """
        )
        deleted_count = cursor.rowcount
        if deleted_count > 0:
            runtime.logger.warning(
                f"🗑️ Deleted {deleted_count} orphaned target_collection_in_sample_batch records due to invalid sample_batch_id."
            )

    elif table_name == "sample_item":
        # Check for sample_item records that have no corresponding sample_file
        cursor.execute(
            """
            DELETE FROM sample_item
            WHERE filename NOT IN (SELECT filename FROM sample_file);
            """
        )
        deleted_count = cursor.rowcount
        if deleted_count > 0:
            runtime.logger.info(
                f"🗑️ Deleted {deleted_count} orphaned sample_item records with missing corresponding sample_file references."
            )

    elif table_name in ["match", "match_isotope", "match_interference"]:
        cursor.execute(
            f"""
            DELETE FROM {table_name}
            WHERE sample_item_id NOT IN (SELECT sample_item_id FROM sample_item);
            """
        )
        deleted_count = cursor.rowcount
        if deleted_count > 0:
            runtime.logger.info(
                f"🗑️ Deleted {deleted_count} orphaned {table_name} records due to invalid sample_item_id."
            )

    # Disable foreign key constraints temporarily to allow for orphans data restore
    cursor.execute("PRAGMA foreign_keys = OFF;")


def create_indexes(conn, table_name, schema_info):
    """
    Creates indexes for the specified table based on the provided schema information.
        - If the index name starts with 'ix_', it creates a UNIQUE index.
        - For any other case, it defaults to creating a regular index.
    """
    cursor = conn.cursor()
    if "indexes" in schema_info:
        # Fetch the current list of indexes on the table
        cursor.execute(f"PRAGMA index_list('{table_name}')")
        existing_indexes = {
            index[1] for index in cursor.fetchall()
        }  # Fetch index names

        for index_sql in schema_info["indexes"]:
            index_name = index_sql.split(" ")[0]
            # Check if the index already exists
            if index_name not in existing_indexes:
                # If the index is prefixed with 'ix_', it is a unique index
                if index_name.startswith("ix_"):
                    cursor.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {index_sql}")
                    runtime.logger.info(f"🆕 Unique index {index_name} created.")
                # Otherwise, create a regular index
                else:
                    cursor.execute(f"CREATE INDEX IF NOT EXISTS {index_sql}")
                    runtime.logger.info(f"🆕 Index {index_name} created.")


def restore_table(conn, table_name, schema_info):
    """
    Handles the restoration of a table's schema if it does not match the expected schema.

    :param conn: The database connection object.
    :type conn: sqlite3.Connection
    :param table_name: Name of the table to be restored.
    :type table_name: str
    :param schema_info: A dictionary containing the expected schema information.
            - 'columns': dict mapping column names to their expected properties - column_name: (type, notnull, dflt_value, pk)
            - 'fks': dict mapping local columns to foreign key details - column_name: (referenced table, referenced column, on update action, on delete action).
    :type schema_info: dict

    PRAGMA Outputs:
        PRAGMA table_info output is organized as follows:
            - cid: Column's ordinal position (starting from zero)
            - name: Column name
            - type: Data type of the column
            - notnull: Whether the column must not be NULL (1 if NOT NULL, 0 otherwise)
            - dflt_value: Default value for the column
            - pk: Whether the column is part of the primary key (1 if it is, 0 otherwise)
        This is transformed into `current_columns` dict with the format:
            {column_name: (type, notnull, dflt_value, pk)}

        PRAGMA foreign_key_list output is organized as follows:
            - id: Foreign key constraint identifier
            - seq: Sequence number (within a foreign key)
            - table: Referenced table name
            - from: Local column name
            - to: Referenced column name
            - on_update: Action on update
            - on_delete: Action on delete
            - match: Match option (always NONE)
        This is transformed into `current_fks` dict with the format:
            {local_column: (referenced_table, referenced_column, on_update_action, on_delete_action)}
    """
    cursor = conn.cursor()
    # Fetch and format the current table schema information
    cursor.execute(f"PRAGMA table_info({table_name})")
    current_columns = {
        col[1]: (col[2], col[3], col[4], col[5]) for col in cursor.fetchall()
    }

    # Fetch and format the current foreign key constraints
    cursor.execute(f"PRAGMA foreign_key_list({table_name})")
    current_fks = {fk[3]: (fk[2], fk[4], fk[5], fk[6]) for fk in cursor.fetchall()}

    runtime.logger.debug(f"Current columns: {current_columns}")
    runtime.logger.debug(f"Correct columns: {schema_info["columns"]}")
    runtime.logger.debug(f"Current foreign keys: {current_fks}")
    runtime.logger.debug(f"Correct foreign keys: {schema_info["fks"]}")
    if current_columns != schema_info["columns"] or current_fks != schema_info["fks"]:
        runtime.logger.warning(f"⚙️ Schema mismatch detected, restoring {table_name}.")
        create_table_backup(cursor, table_name)
        update_backup_table(cursor, table_name)
        drop_table(cursor, table_name)
        cursor.execute(schema_info["create_sql"])  # create table with correct schema
        restore_data_from_backup(cursor, table_name, schema_info["columns"].keys())
        runtime.logger.info(f"Schema restoration of {table_name} completed.")
    else:
        runtime.logger.info(
            f"✅ Schema of {table_name} is correct, no restoration needed."
        )
