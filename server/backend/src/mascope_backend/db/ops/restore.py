"""
Database restoration operations for schema validation and orphan cleanup.

This module provides functionality to:
- Validate table schemas against expected configurations
- Restore tables to correct schema when mismatches are detected
- Delete orphaned records that violate foreign key constraints
- Create missing indexes for query performance
"""

import asyncio
import gc
import os
import sqlite3

from mascope_backend.db.ops.backup import create_db_backup
from mascope_backend.db.tables_config import get_table_configs
from mascope_backend.db.utils import get_current_db_version
from mascope_backend.runtime import runtime


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
    gc.collect()
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
    await loop.run_in_executor(None, delete_all_orphaned_records_sync, db_path)

    # Step 5: Create indexes after restoring schema and cleaning up orphans
    runtime.logger.info("Checking for missing indexes...")
    indexes_created = await loop.run_in_executor(
        None, create_all_indexes_sync, db_path, tables_to_restore, table_configs
    )

    if indexes_created == 0:
        runtime.logger.info("✅ All indexes present - no missing indexes found!")


# -----------------------------
# CLI entry point for synchronous execution
# -----------------------------


def run_db_restore(tables: list[str] | None = None):
    """
    Orchestrates the schema restoration process for specified database tables in synchronous mode.

    :param tables: List of tables to restore. If None, all tables will be restored, defaults to None
    :type tables: list[str] | None, optional
    """

    # Run the async function with the specified tables
    asyncio.run(db_restore(tables))


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


def delete_all_orphaned_records_sync(db_path):
    """
    Synchronously delete all orphaned records across all tables.
    """
    with sqlite3.connect(db_path) as conn:
        delete_all_orphaned_records(conn)
        conn.commit()


def create_all_indexes_sync(db_path, tables_to_restore, table_configs):
    """
    Synchronously create all missing indexes and return count.
    """
    total_created = 0
    with sqlite3.connect(db_path) as conn:
        for table_name in tables_to_restore:
            created = create_indexes(conn, table_name, table_configs[table_name])
            total_created += created
        conn.commit()
    return total_created


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


def delete_all_orphaned_records(conn):
    """
    Orphan cleanup using table_configs to determine FK relationships.

    Processes tables in dependency order so that parent records are not deleted
    before checking child records. Handles both CASCADE and SET NULL relationships.

    :param conn: Database connection object.
    """
    cursor = conn.cursor()

    # Enable foreign key constraint enforcement
    cursor.execute("PRAGMA foreign_keys = ON;")

    table_configs = get_table_configs()
    total_deleted = 0

    # Define processing order: children first, then parents
    orphan_check_order = [
        # Match tables (deepest children - depend on sample_item and targets)
        "match_isotope",
        "match_rating",
        "match_ion",
        "match_compound",
        "match_collection",
        "match_sample",
        # Sample hierarchy
        "sample_item",  # depends on sample_file and sample_batch
        # Junction tables
        "target_collection_in_sample_batch",
        "target_compound_in_target_collection",
        # Target hierarchy
        "target_isotope",  # depends on target_ion
        "target_ion",  # depends on target_compound and ionization_mechanism
        # Sample batch
        "sample_batch",  # depends on workspace
        # Auth
        "access_token",  # depends on user
    ]

    for table_name in orphan_check_order:
        if table_name not in table_configs:
            continue

        table_config = table_configs[table_name]

        # Skip if no foreign keys
        if "fks" not in table_config or not table_config["fks"]:
            continue

        # Check each foreign key relationship
        for local_col, (ref_table, ref_col, on_update, on_delete) in table_config[
            "fks"
        ].items():

            # Only check CASCADE relationships (SET NULL shouldn't create orphans)
            if on_delete == "CASCADE":
                deleted = _delete_orphans_for_fk(
                    cursor, table_name, local_col, ref_table, ref_col
                )
                total_deleted += deleted

    if total_deleted == 0:
        runtime.logger.info(
            "✅ No orphaned records found - database integrity verified!"
        )
    else:
        runtime.logger.warning(f"⚠️ Total orphaned records deleted: {total_deleted}")


def _delete_orphans_for_fk(cursor, table_name, local_col, ref_table, ref_col):
    """
    Delete orphaned records for a specific foreign key relationship.

    :param cursor: Database cursor
    :param table_name: Table containing the foreign key
    :param local_col: Local column name
    :param ref_table: Referenced table name
    :param ref_col: Referenced column name
    :return: Number of deleted records
    """
    # Delete records where FK points to non-existent parent
    query = f"""
        DELETE FROM {table_name}
        WHERE {local_col} NOT IN (
            SELECT {ref_col} FROM {ref_table}
        );
    """

    cursor.execute(query)
    deleted_count = cursor.rowcount

    if deleted_count > 0:
        runtime.logger.info(
            f"🗑️  Deleted {deleted_count} orphaned {table_name} records "
            f"(FK {local_col} references non-existent {ref_table}.{ref_col})"
        )

    return deleted_count


def create_indexes(conn, table_name, schema_info):
    """
    Creates indexes for the specified table based on the provided schema information.
    Returns the number of indexes created.

    :param conn: Database connection
    :param table_name: Name of table to create indexes for
    :param schema_info: Schema configuration dict
    :return: Number of indexes created
    """
    cursor = conn.cursor()
    indexes_created = 0

    if "indexes" not in schema_info:
        return 0

    # Fetch the current list of indexes on the table
    cursor.execute(f"PRAGMA index_list('{table_name}')")
    existing_indexes = {index[1] for index in cursor.fetchall()}  # Fetch index names

    for index_sql in schema_info["indexes"]:
        index_name = index_sql.split(" ")[0]
        # Check if the index already exists
        if index_name not in existing_indexes:
            # If the index is prefixed with 'ix_', it is a unique index
            if index_name.startswith("ix_"):
                cursor.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {index_sql}")
                runtime.logger.info(
                    f"🆕 Created unique index {index_name} on {table_name}"
                )
            # Otherwise, create a regular index
            else:
                cursor.execute(f"CREATE INDEX IF NOT EXISTS {index_sql}")
                runtime.logger.info(f"🆕 Created index {index_name} on {table_name}")
            indexes_created += 1

    return indexes_created


def normalize_default_value(value):
    """
    Normalize default values for schema comparison.

    SQLite PRAGMA table_info returns string defaults with quotes included,
    but table configs may have them without quotes. This function normalizes
    both formats for consistent comparison.

    :param value: Default value from PRAGMA or table config
    :return: Normalized default value
    """
    if value and isinstance(value, str):
        # Check if it's a quoted string value
        if value.startswith("'") and value.endswith("'") and len(value) > 2:
            return value[1:-1]  # Strip outer quotes
    return value


def normalize_columns_for_comparison(columns_dict):
    """
    Normalize column definitions for comparison by normalizing default values.

    :param columns_dict: Dictionary of column definitions
    :return: Normalized dictionary with default values normalized
    """
    normalized = {}
    for col_name, (col_type, notnull, default_val, pk) in columns_dict.items():
        normalized_default = normalize_default_value(default_val)
        normalized[col_name] = (col_type, notnull, normalized_default, pk)
    return normalized


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

    # Normalize columns for comparison (handles string default value quirks)
    normalized_current_columns = normalize_columns_for_comparison(current_columns)
    normalized_expected_columns = normalize_columns_for_comparison(
        schema_info["columns"]
    )

    runtime.logger.debug(f"Current columns: {normalized_current_columns}")
    runtime.logger.debug(f"Correct columns: {normalized_expected_columns}")
    runtime.logger.debug(f"Current foreign keys: {current_fks}")
    runtime.logger.debug(f"Correct foreign keys: {schema_info['fks']}")

    # Compare normalized schemas
    if (
        normalized_current_columns != normalized_expected_columns
        or current_fks != schema_info["fks"]
    ):
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
