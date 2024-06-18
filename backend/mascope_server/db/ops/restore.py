import os
import sqlite3
import sys
from mascope_server.db import get_current_db_version, create_db_backup


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

    elif table_name in ["match", "match_interference"]:
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
    data_path = os.environ.get("MASCOPE_PRIVATE_DATABASE_DIR")
    current_version = get_current_db_version()
    db_path = os.path.join(data_path, f"mascope.v{current_version}.db")
    create_db_backup(db_path, "restore")

    # Restore schema for specified tables or all cinfigured tables
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


# Schema configuration for database tables. Each key in the dictionary is a table name,
# and its value is a dictionary specifying details about the table's schema and configuration.

# Structure:
# - 'columns': Dictionary mapping column names to their properties:
#   - column_name: (type, notnull, default_value, primary_key_flag)
#     - type: Data type of the column as a string.
#     - notnull: Boolean flag (1 if NOT NULL constraint is applied, 0 otherwise).
#     - default_value: Default value for the column, or None if no default is specified.
#     - primary_key_flag: Boolean flag (1 if the column is part of the primary key, 0 otherwise).

# - 'fks': Dictionary mapping local columns to foreign key details:
#   - column_name: (referenced_table, referenced_column, on_update_action, on_delete_action)
#     - referenced_table: Name of the table that the foreign key points to.
#     - referenced_column: Name of the column in the referenced table.
#     - on_update_action: Action to take on update of the referenced key.
#     - on_delete_action: Action to take on delete of the referenced key.

# - 'create_sql': String containing the SQL command to create the table. This should include
#   all column definitions, constraints, and table-specific attributes necessary for table creation.

# - 'indexes': List of strings, each representing an SQL command to create an index on the table.
#   - This is optional and may not be present in all table configurations.

table_configs = {
    "workspace": {
        "columns": {
            "workspace_id": ("VARCHAR(16)", 1, None, 1),
            "workspace_name": ("VARCHAR(256)", 1, None, 0),
            "workspace_description": ("TEXT", 0, None, 0),
            "workspace_utc_created": ("TIMESTAMP", 0, None, 0),
            "workspace_utc_modified": ("TIMESTAMP", 0, None, 0),
        },
        "fks": {},
        "create_sql": """
            CREATE TABLE workspace (
                workspace_id VARCHAR(16) NOT NULL PRIMARY KEY,
                workspace_name VARCHAR(256) NOT NULL,
                workspace_description TEXT,
                workspace_utc_created TIMESTAMP,
                workspace_utc_modified TIMESTAMP
            );
        """,
    },
    "attribute_template": {
        "columns": {
            "attribute_template_id": ("VARCHAR(16)", 1, None, 1),
            "name": ("VARCHAR(256)", 1, None, 0),
            "type": ("VARCHAR(64)", 0, None, 0),
            "template": ("JSON", 0, None, 0),
        },
        "fks": {},
        "create_sql": """
            CREATE TABLE attribute_template (
                attribute_template_id VARCHAR(16) NOT NULL PRIMARY KEY,
                name VARCHAR(256) NOT NULL,
                type VARCHAR(64),
                template JSON
            );
        """,
    },
    "instrument_function": {
        "columns": {
            "instrument_function_id": ("VARCHAR(32)", 1, None, 1),
            "instrument": ("VARCHAR(64)", 1, None, 0),
            "datetime_utc": ("TIMESTAMP", 0, None, 0),
            "peakshape": ("JSON", 0, None, 0),
            "resolution_function": ("JSON", 0, None, 0),
        },
        "fks": {},
        "create_sql": """
            CREATE TABLE instrument_function (
                instrument_function_id VARCHAR(32) NOT NULL PRIMARY KEY,
                instrument VARCHAR(64) NOT NULL,
                datetime_utc TIMESTAMP,
                peakshape JSON,
                resolution_function JSON
            );
        """,
    },
    "ionization_mechanism": {
        "columns": {
            "ionization_mechanism_id": ("VARCHAR(16)", 1, None, 1),
            "ionization_mechanism_polarity": ("VARCHAR(1)", 1, None, 0),
            "ionization_mechanism": ("VARCHAR", 0, None, 0),
            "reagent": ("VARCHAR", 0, None, 0),
        },
        "fks": {},
        "create_sql": """
            CREATE TABLE ionization_mechanism (
                ionization_mechanism_id VARCHAR(16) NOT NULL PRIMARY KEY,
                ionization_mechanism_polarity VARCHAR(1) NOT NULL,
                ionization_mechanism VARCHAR,
                reagent VARCHAR
            );
        """,
    },
    "target_compound": {
        "columns": {
            "target_compound_id": ("VARCHAR(16)", 1, None, 1),
            "target_compound_name": ("TEXT", 0, None, 0),
            "target_compound_formula": ("VARCHAR(256)", 1, None, 0),
            "cas_number": ("VARCHAR(12)", 0, None, 0),
        },
        "fks": {},
        "create_sql": """
            CREATE TABLE target_compound (
                target_compound_id VARCHAR(16) NOT NULL PRIMARY KEY,
                target_compound_name TEXT,
                target_compound_formula VARCHAR(256) NOT NULL,
                cas_number VARCHAR(12)
            );
        """,
    },
    "target_collection": {
        "columns": {
            "target_collection_id": ("VARCHAR(16)", 1, None, 1),
            "target_collection_name": ("VARCHAR(256)", 1, None, 0),
            "target_collection_description": ("TEXT", 0, None, 0),
            "target_collection_type": ("VARCHAR(64)", 1, "'TARGETS'", 0),
        },
        "fks": {},
        "create_sql": """
            CREATE TABLE target_collection (
                target_collection_id VARCHAR(16) NOT NULL PRIMARY KEY,
                target_collection_name VARCHAR(256) NOT NULL,
                target_collection_description TEXT,
                target_collection_type VARCHAR(64) NOT NULL DEFAULT 'TARGETS'
            );
        """,
    },
    "target_ion": {
        "columns": {
            "target_ion_id": ("VARCHAR(16)", 1, None, 1),
            "target_compound_id": ("VARCHAR(16)", 1, None, 0),
            "ionization_mechanism_id": ("VARCHAR(16)", 1, None, 0),
            "target_ion_formula": ("VARCHAR(256)", 1, None, 0),
            "filter_params": ("JSON", 0, None, 0),
        },
        "fks": {
            "ionization_mechanism_id": (
                "ionization_mechanism",
                "ionization_mechanism_id",
                "NO ACTION",
                "CASCADE",
            ),
            "target_compound_id": (
                "target_compound",
                "target_compound_id",
                "NO ACTION",
                "CASCADE",
            ),
        },
        "create_sql": """
            CREATE TABLE target_ion (
                target_ion_id VARCHAR(16) NOT NULL PRIMARY KEY,
                target_compound_id VARCHAR(16) NOT NULL
                    REFERENCES target_compound(target_compound_id) ON DELETE CASCADE,
                ionization_mechanism_id VARCHAR(16) NOT NULL
                    REFERENCES ionization_mechanism(ionization_mechanism_id) ON DELETE CASCADE,
                target_ion_formula VARCHAR(256) NOT NULL,
                filter_params JSON
            );
        """,
        "indexes": [
            "idx_target_ion_ionization_mechanism ON target_ion (ionization_mechanism_id)"  # ok
        ],
    },
    "target_isotope": {
        "columns": {
            "target_isotope_id": ("VARCHAR(16)", 1, None, 1),
            "target_ion_id": ("VARCHAR(16)", 1, None, 0),
            "mz": ("FLOAT", 1, None, 0),
            "relative_abundance": ("FLOAT", 1, None, 0),
        },
        "fks": {
            "target_ion_id": (
                "target_ion",
                "target_ion_id",
                "NO ACTION",
                "CASCADE",
            ),
        },
        "create_sql": """
            CREATE TABLE target_isotope (
                target_isotope_id VARCHAR(16) NOT NULL PRIMARY KEY,
                target_ion_id VARCHAR(16) NOT NULL
                    REFERENCES target_ion(target_ion_id) ON DELETE CASCADE,
                mz FLOAT NOT NULL,
                relative_abundance FLOAT NOT NULL
                    CHECK (relative_abundance BETWEEN 0 AND 1)
            );
        """,
    },
    "target_collection_in_sample_batch": {
        "columns": {
            "target_collection_id": ("VARCHAR(16)", 1, None, 1),
            "sample_batch_id": ("VARCHAR(16)", 1, None, 2),
        },
        "fks": {
            "sample_batch_id": (
                "sample_batch",
                "sample_batch_id",
                "NO ACTION",
                "CASCADE",
            ),
            "target_collection_id": (
                "target_collection",
                "target_collection_id",
                "NO ACTION",
                "CASCADE",
            ),
        },
        "create_sql": """
            CREATE TABLE target_collection_in_sample_batch (
                target_collection_id VARCHAR(16) NOT NULL
                    REFERENCES target_collection(target_collection_id) ON DELETE CASCADE,
                sample_batch_id VARCHAR(16) NOT NULL
                    REFERENCES sample_batch(sample_batch_id) ON DELETE CASCADE,
                PRIMARY KEY
                    (target_collection_id, sample_batch_id)
            );
        """,
    },
    "target_compound_in_target_collection": {
        "columns": {
            "target_compound_id": ("VARCHAR(16)", 1, None, 1),
            "target_collection_id": ("VARCHAR(16)", 1, None, 2),
        },
        "fks": {
            "target_collection_id": (
                "target_collection",
                "target_collection_id",
                "NO ACTION",
                "CASCADE",
            ),
            "target_compound_id": (
                "target_compound",
                "target_compound_id",
                "NO ACTION",
                "CASCADE",
            ),
        },
        "create_sql": """
            CREATE TABLE target_compound_in_target_collection (
                target_compound_id VARCHAR(16) NOT NULL
                    REFERENCES target_compound(target_compound_id) ON DELETE CASCADE,
                target_collection_id VARCHAR(16) NOT NULL
                    REFERENCES target_collection(target_collection_id) ON DELETE CASCADE,
                PRIMARY KEY
                    (target_compound_id, target_collection_id)
            );
        """,
    },
    "match": {
        "columns": {
            "match_id": ("VARCHAR(32)", 1, None, 1),
            "target_isotope_id": ("VARCHAR(16)", 1, None, 0),
            "sample_item_id": ("VARCHAR(16)", 1, None, 0),
            "sample_peak_id": ("INT", 1, None, 0),
            "sample_peak_mz": ("FLOAT", 1, None, 0),
            "sample_peak_area": ("FLOAT", 1, None, 0),
            "sample_peak_area_relative": ("FLOAT", 1, None, 0),
            "sample_peak_tof": ("FLOAT", 1, None, 0),
            "match_abundance_error": ("FLOAT", 1, None, 0),
            "match_mz_error": ("FLOAT", 1, None, 0),
            "match_score": ("FLOAT", 1, None, 0),
            "match_isotope_correlation": ("FLOAT", 1, None, 0),
        },
        "fks": {
            "sample_item_id": (
                "sample_item",
                "sample_item_id",
                "NO ACTION",
                "CASCADE",
            ),
            "target_isotope_id": (
                "target_isotope",
                "target_isotope_id",
                "NO ACTION",
                "CASCADE",
            ),
        },
        "create_sql": """
            CREATE TABLE match (
                match_id VARCHAR(32) NOT NULL PRIMARY KEY,
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
                match_score FLOAT NOT NULL
                    CHECK (match_score BETWEEN 0 AND 1),
                match_isotope_correlation FLOAT NOT NULL
            );
        """,
        "indexes": [
            "idx_match_sample_item ON match (sample_item_id)",
        ],
    },
    "match_interference": {
        "columns": {
            "match_interference_id": ("VARCHAR(32)", 1, None, 1),
            "target_isotope_id": ("VARCHAR(16)", 1, None, 0),
            "sample_item_id": ("VARCHAR(16)", 1, None, 0),
            "sample_peak_interference": ("FLOAT", 1, None, 0),
        },
        "fks": {
            "target_isotope_id": (
                "target_isotope",
                "target_isotope_id",
                "NO ACTION",
                "CASCADE",
            ),
            "sample_item_id": (
                "sample_item",
                "sample_item_id",
                "NO ACTION",
                "CASCADE",
            ),
        },
        "create_sql": """
            CREATE TABLE match_interference (
                match_interference_id VARCHAR(32) NOT NULL PRIMARY KEY,
                target_isotope_id VARCHAR(16) NOT NULL
                    REFERENCES target_isotope(target_isotope_id) ON DELETE CASCADE,
                sample_item_id VARCHAR(16) NOT NULL
                    REFERENCES sample_item(sample_item_id) ON DELETE CASCADE,
                sample_peak_interference FLOAT NOT NULL
            );
        """,
        "indexes": [
            "idx_match_interference_sample_item ON match_interference (sample_item_id)",
        ],
    },
    "match_rating": {
        "columns": {
            "match_rating_id": ("VARCHAR(32)", 1, None, 1),
            "sample_item_id": ("VARCHAR(16)", 1, None, 0),
            "target_ion_id": ("VARCHAR(16)", 1, None, 0),
            "match_rating_utc_created": ("TIMESTAMP", 0, None, 0),
            "rating": ("INT", 1, None, 0),
            "checklist": ("JSON", 0, None, 0),
            "environment": ("JSON", 0, None, 0),
        },
        "fks": {
            "target_ion_id": (
                "target_ion",
                "target_ion_id",
                "NO ACTION",
                "CASCADE",
            ),
            "sample_item_id": (
                "sample_item",
                "sample_item_id",
                "NO ACTION",
                "CASCADE",
            ),
        },
        "create_sql": """
            CREATE TABLE match_rating (
                match_rating_id VARCHAR(32) NOT NULL PRIMARY KEY,
                sample_item_id VARCHAR(16) NOT NULL
                    REFERENCES sample_item(sample_item_id) ON DELETE CASCADE,
                target_ion_id VARCHAR(16) NOT NULL
                    REFERENCES target_ion(target_ion_id) ON DELETE CASCADE,
                match_rating_utc_created TIMESTAMP,
                rating INT NOT NULL CHECK (rating BETWEEN 0 AND 2),
                checklist JSON,
                environment JSON
            );
        """,
    },
    # TODO_db issue #376
    "sample_item": {
        "columns": {
            "sample_item_id": ("VARCHAR(16)", 1, None, 1),
            "sample_batch_id": ("VARCHAR(16)", 1, None, 0),
            "filename": ("VARCHAR(256)", 1, None, 0),
            "sample_item_name": ("VARCHAR(256)", 1, None, 0),
            "sample_item_type": ("VARCHAR(64)", 1, None, 0),
            "sample_item_attributes": ("JSON", 0, None, 0),
            "sample_item_utc_created": ("TIMESTAMP", 0, None, 0),
            "sample_item_utc_modified": ("TIMESTAMP", 0, None, 0),
            "filter_id": ("VARCHAR(6)", 0, None, 0),
        },
        "fks": {
            "sample_batch_id": (
                "sample_batch",
                "sample_batch_id",
                "NO ACTION",
                "CASCADE",
            )
        },
        "create_sql": """
            CREATE TABLE sample_item (
                sample_item_id VARCHAR(16) NOT NULL PRIMARY KEY,
                sample_batch_id VARCHAR(16) NOT NULL
                    REFERENCES sample_batch(sample_batch_id) ON DELETE CASCADE,
                filename VARCHAR(256) NOT NULL,
                sample_item_name VARCHAR(256) NOT NULL,
                sample_item_type VARCHAR(64) NOT NULL,
                sample_item_attributes JSON,
                sample_item_utc_created TIMESTAMP,
                sample_item_utc_modified TIMESTAMP,
                filter_id VARCHAR(6)
            );
        """,
        "indexes": [
            "idx_sample_item_sample_batch ON sample_item (sample_batch_id)",
        ],
    },
    # TODO_db issue #376
    "sample_file": {
        "columns": {
            "sample_file_id": ("VARCHAR(16)", 1, None, 1),
            "filename": ("VARCHAR(256)", 1, None, 0),
            "instrument": ("VARCHAR(64)", 0, None, 0),
            "datetime": ("TIMESTAMP WITH TIME ZONE", 0, None, 0),
            "datetime_utc": ("TIMESTAMP", 0, None, 0),
            "length": ("FLOAT", 0, None, 0),
            "range": ("JSON", 0, None, 0),
            "mz_calibration": ("JSON", 0, None, 0),
            "tic": ("FLOAT", 0, None, 0),
            "polarity": ("VARCHAR(1)", 0, None, 0),
        },
        "fks": {},
        "create_sql": """
        CREATE TABLE sample_file (
            sample_file_id VARCHAR(16) NOT NULL PRIMARY KEY,
            filename VARCHAR(256) NOT NULL UNIQUE,
            instrument VARCHAR(64),
            datetime TIMESTAMP WITH TIME ZONE,
            datetime_utc TIMESTAMP,
            length FLOAT,
            range JSON,
            mz_calibration JSON,
            tic FLOAT,
            polarity VARCHAR(1)
        );
    """,
    },
    "sample_batch": {
        "columns": {
            "sample_batch_id": ("VARCHAR(16)", 1, None, 1),
            "workspace_id": ("VARCHAR(16)", 1, None, 0),
            "sample_batch_name": ("VARCHAR", 1, None, 0),
            "sample_batch_description": ("TEXT", 0, None, 0),
            "build_params": ("JSON", 0, None, 0),
            "sample_batch_utc_created": ("TIMESTAMP", 0, None, 0),
            "sample_batch_utc_modified": ("TIMESTAMP", 0, None, 0),
        },
        "fks": {
            "workspace_id": ("workspace", "workspace_id", "NO ACTION", "CASCADE"),
        },
        "create_sql": """
            CREATE TABLE sample_batch (
                sample_batch_id VARCHAR(16) NOT NULL PRIMARY KEY,
                workspace_id VARCHAR(16) NOT NULL 
                    REFERENCES workspace(workspace_id) ON DELETE CASCADE,
                sample_batch_name VARCHAR NOT NULL,
                sample_batch_description TEXT,
                build_params JSON,
                sample_batch_utc_created TIMESTAMP,
                sample_batch_utc_modified TIMESTAMP
            );
        """,
    },
}
