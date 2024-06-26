import os
import sqlite3
import sys

from mascope_server.db import get_current_db_version, create_db_backup
from mascope_server.db.tables_config import get_table_configs
from mascope_server.config import config


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
            print(
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
            print(
                f"🗑️ Deleted {deleted_count} orphaned target_compound_in_target_collection records due to invalid target_compound_id."
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
            print(
                f"🗑️ Deleted {deleted_count} orphaned {table_name} records due to invalid sample_item_id."
            )

    # Disable foreign key constraints temporarily to allow for orphans data restore
    cursor.execute("PRAGMA foreign_keys = OFF;")


def create_indexes(conn, table_name, schema_info):
    """
    Creates indexes for the specified table based on the provided schema information.
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
            # Execute index creation if it doesn't already exist
            if index_name not in existing_indexes:
                cursor.execute(f"CREATE INDEX IF NOT EXISTS {index_sql}")
                print(f"➕ Index {index_name} created.")


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
    # TODO_debug_mode Debug mode conditional printing
    # print("current_columns", current_columns)
    # print("correct_columns", schema_info["columns"])
    # print("current_fks", current_fks)
    # print("correct_fks", schema_info["fks"])

    if current_columns != schema_info["columns"] or current_fks != schema_info["fks"]:
        print(f"⚙️ Schema mismatch detected, restoring {table_name}.")
        create_table_backup(cursor, table_name)
        update_backup_table(cursor, table_name)
        drop_table(cursor, table_name)
        cursor.execute(schema_info["create_sql"])  # create table with correct schema
        restore_data_from_backup(cursor, table_name, schema_info["columns"].keys())
        print(f"Schema restoration of {table_name} completed.")
    else:
        print(f"✅ Schema of {table_name} is correct, no restoration needed.")


def run_db_restore():
    """
    Orchestrates the schema restoration process for specified database tables.

    1. Backs up the current database.
    2. Iterates through the specified in command tables or all configured tables if none are explicitly specified.
    3. Restores the schema for each table to ensure it matches the expected configuration by:
       - Restoring the table schema and data.
       - Deleting any orphaned records that do not comply with foreign key constraints.
       - Creating necessary indexes if they do not exist.

    Uses separate database connections for each major step to ensure changes are applied correctly and
    to manage database transactions effectively.
    """
    data_path = config.server.database
    current_version = get_current_db_version()
    db_path = os.path.join(data_path, f"mascope.v{current_version}.db")
    create_db_backup(db_path, "restore")

    # Get table configs for current version or most recent config
    table_configs = get_table_configs(current_version)
    # Restore schema for specified tables or all configured tables
    tables_to_restore = sys.argv[1:] if len(sys.argv) > 1 else table_configs.keys()

    for table_name in tables_to_restore:
        if table_name in table_configs:
            # Separate connection for restoring table
            with sqlite3.connect(db_path) as conn:
                restore_table(conn, table_name, table_configs[table_name])
                conn.commit()
            # Separate connection for deleting orphaned records
            with sqlite3.connect(db_path) as conn:
                delete_orphaned_records(conn, table_name)
                conn.commit()
            # Separate connection for creating indexes
            with sqlite3.connect(db_path) as conn:
                create_indexes(conn, table_name, table_configs[table_name])
                conn.commit()
        else:
            print(
                f"No configuration found for '{table_name}'. Please check your table name or define its configuration."
            )
