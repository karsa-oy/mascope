"""
Schema configuration for v18 database tables. Each key in the dictionary is a table name,
and its value is a dictionary specifying details about the table's schema and configuration.

Structure:
- 'columns': Dictionary mapping column names to their properties:
  - column_name: (type, notnull, default_value, primary_key_flag)
    - type: Data type of the column as a string.
    - notnull: Boolean flag (1 if NOT NULL constraint is applied, 0 otherwise).
    - default_value: Default value for the column, or None if no default is specified.
    - primary_key_flag: Boolean flag (1 if the column is part of the primary key, 0 otherwise).

- 'fks': Dictionary mapping local columns to foreign key details:
  - column_name: (referenced_table, referenced_column, on_update_action, on_delete_action)
    - referenced_table: Name of the table that the foreign key points to.
    - referenced_column: Name of the column in the referenced table.
    - on_update_action: Action to take on update of the referenced key.
    - on_delete_action: Action to take on delete of the referenced key.

- 'create_sql': String containing the SQL command to create the table. This should include
  all column definitions, constraints, and table-specific attributes necessary for table creation.

- 'indexes': List of strings, each representing an SQL command to create an index on the table.
  - This is optional and may not be present in all table configurations.
"""

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
            "method_file": ("VARCHAR(256)", 1, None, 0),
            "datetime_utc": ("TIMESTAMP", 1, None, 0),
            "peakshape": ("JSON", 0, None, 0),
            "resolution_function": ("JSON", 0, None, 0),
        },
        "fks": {},
        "create_sql": """
            CREATE TABLE instrument_function (
                instrument_function_id VARCHAR(32) NOT NULL, 
                instrument VARCHAR(64) NOT NULL, 
                method_file VARCHAR(256) NOT NULL, 
                datetime_utc TIMESTAMP NOT NULL, 
                peakshape JSON, 
                resolution_function JSON, 
                PRIMARY KEY (instrument_function_id)
            );
    """,
    },
    "ionization_mechanism": {
        "columns": {
            "ionization_mechanism_id": ("VARCHAR(16)", 1, None, 1),
            "ionization_mechanism_polarity": ("VARCHAR(1)", 1, None, 0),
            "ionization_mechanism": ("VARCHAR", 1, None, 0),
            "reagent": ("VARCHAR", 0, None, 0),
        },
        "fks": {},
        "create_sql": """
            CREATE TABLE ionization_mechanism (
                ionization_mechanism_id VARCHAR(16) NOT NULL PRIMARY KEY,
                ionization_mechanism_polarity VARCHAR(1) NOT NULL,
                ionization_mechanism VARCHAR NOT NULL,
                reagent VARCHAR,
                UNIQUE (ionization_mechanism)
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
    "match_sample": {
        "columns": {
            "match_sample_id": ("VARCHAR(32)", 1, None, 1),
            "sample_item_id": ("VARCHAR(16)", 1, None, 0),
            "match_score": ("FLOAT", 1, None, 0),
            "match_category": ("INTEGER", 1, None, 0),
            "sample_peak_area_sum": ("FLOAT", 1, None, 0),
            "sample_peak_interference_sum": ("FLOAT", 1, None, 0),
            "match_sample_utc_created": ("TIMESTAMP", 0, None, 0),
            "match_sample_utc_modified": ("TIMESTAMP", 0, None, 0),
        },
        "fks": {
            "sample_item_id": ("sample_item", "sample_item_id", "NO ACTION", "CASCADE"),
        },
        "create_sql": """
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
    """,
        "indexes": [
            "idx_match_sample_sample_item ON match_sample (sample_item_id)",
        ],
    },
    "match_collection": {
        "columns": {
            "match_collection_id": ("VARCHAR(32)", 1, None, 1),
            "sample_item_id": ("VARCHAR(16)", 1, None, 0),
            "target_collection_id": ("VARCHAR(16)", 1, None, 0),
            "match_score": ("FLOAT", 1, None, 0),
            "match_category": ("INTEGER", 1, None, 0),
            "sample_peak_area_sum": ("FLOAT", 1, None, 0),
            "sample_peak_interference_sum": ("FLOAT", 1, None, 0),
            "match_collection_utc_created": ("TIMESTAMP", 0, None, 0),
            "match_collection_utc_modified": ("TIMESTAMP", 0, None, 0),
        },
        "fks": {
            "target_collection_id": (
                "target_collection",
                "target_collection_id",
                "NO ACTION",
                "CASCADE",
            ),
            "sample_item_id": ("sample_item", "sample_item_id", "NO ACTION", "CASCADE"),
        },
        "create_sql": """
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
    """,
        "indexes": [
            "idx_match_collection_sample_item ON match_collection (sample_item_id)",
        ],
    },
    "match_compound": {
        "columns": {
            "match_compound_id": ("VARCHAR(32)", 1, None, 1),
            "sample_item_id": ("VARCHAR(16)", 1, None, 0),
            "target_compound_id": ("VARCHAR(16)", 1, None, 0),
            "match_score": ("FLOAT", 1, None, 0),
            "match_category": ("INTEGER", 1, None, 0),
            "sample_peak_area_sum": ("FLOAT", 1, None, 0),
            "sample_peak_interference_sum": ("FLOAT", 1, None, 0),
            "match_compound_utc_created": ("TIMESTAMP", 0, None, 0),
            "match_compound_utc_modified": ("TIMESTAMP", 0, None, 0),
        },
        "fks": {
            "target_compound_id": (
                "target_compound",
                "target_compound_id",
                "NO ACTION",
                "CASCADE",
            ),
            "sample_item_id": ("sample_item", "sample_item_id", "NO ACTION", "CASCADE"),
        },
        "create_sql": """
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
    """,
        "indexes": [
            "idx_match_compound_sample_item ON match_compound (sample_item_id)",
        ],
    },
    "match_ion": {
        "columns": {
            "match_ion_id": ("VARCHAR(32)", 1, None, 1),
            "sample_item_id": ("VARCHAR(16)", 1, None, 0),
            "target_ion_id": ("VARCHAR(16)", 1, None, 0),
            "match_score": ("FLOAT", 1, None, 0),
            "match_category": ("INTEGER", 1, None, 0),
            "sample_peak_area_sum": ("FLOAT", 1, None, 0),
            "sample_peak_interference_sum": ("FLOAT", 1, None, 0),
            "match_ion_utc_created": ("TIMESTAMP", 0, None, 0),
            "match_ion_utc_modified": ("TIMESTAMP", 0, None, 0),
        },
        "fks": {
            "target_ion_id": ("target_ion", "target_ion_id", "NO ACTION", "CASCADE"),
            "sample_item_id": ("sample_item", "sample_item_id", "NO ACTION", "CASCADE"),
        },
        "create_sql": """
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
    """,
        "indexes": [
            "idx_match_ion_sample_item ON match_ion (sample_item_id)",
        ],
    },
    "match_isotope": {
        "columns": {
            "match_isotope_id": ("VARCHAR(32)", 1, None, 1),
            "target_isotope_id": ("VARCHAR(16)", 1, None, 0),
            "sample_item_id": ("VARCHAR(16)", 1, None, 0),
            "sample_peak_id": ("INTEGER", 1, None, 0),
            "sample_peak_mz": ("FLOAT", 1, None, 0),
            "sample_peak_area": ("FLOAT", 1, None, 0),
            "sample_peak_area_relative": ("FLOAT", 1, None, 0),
            "sample_peak_tof": ("FLOAT", 1, None, 0),
            "match_abundance_error": ("FLOAT", 1, None, 0),
            "match_mz_error": ("FLOAT", 1, None, 0),
            "match_isotope_correlation": ("FLOAT", 1, None, 0),
            "match_score": ("FLOAT", 1, None, 0),
            "match_isotope_utc_created": ("TIMESTAMP", 0, None, 0),
            "match_isotope_utc_modified": ("TIMESTAMP", 0, None, 0),
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
            CREATE TABLE match_isotope (
                match_isotope_id VARCHAR(32) NOT NULL PRIMARY KEY,
                target_isotope_id VARCHAR(16) NOT NULL
                    REFERENCES target_isotope(target_isotope_id) ON DELETE CASCADE,
                sample_item_id VARCHAR(16) NOT NULL
                    REFERENCES sample_item(sample_item_id) ON DELETE CASCADE,
                sample_peak_id INTEGER NOT NULL,
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
        """,
        "indexes": [
            "idx_match_isotope_sample_item ON match_isotope (sample_item_id)",
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
            "rating": ("INTEGER", 1, None, 0),
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
                rating INTEGER NOT NULL CHECK (rating BETWEEN 0 AND 2),
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
            "instrument_function_id": ("VARCHAR(32)", 0, None, 0),
            "filename": ("VARCHAR(256)", 1, None, 0),
            "instrument": ("VARCHAR(64)", 0, None, 0),
            "method_file": ("VARCHAR(256)", 0, None, 0),
            "datetime": ("TIMESTAMP", 0, None, 0),
            "datetime_utc": ("TIMESTAMP", 0, None, 0),
            "length": ("FLOAT", 0, None, 0),
            "range": ("JSON", 0, None, 0),
            "mz_calibration": ("JSON", 0, None, 0),
            "tic": ("FLOAT", 0, None, 0),
            "polarity": ("VARCHAR(1)", 0, None, 0),
        },
        "fks": {
            "instrument_function_id": (
                "instrument_function",
                "instrument_function_id",
                "NO ACTION",
                "SET NULL",
            ),
        },
        "create_sql": """
            CREATE TABLE sample_file (
                sample_file_id VARCHAR(16) NOT NULL, 
                instrument_function_id VARCHAR(32), 
                filename VARCHAR(256) NOT NULL, 
                instrument VARCHAR(64), 
                method_file VARCHAR(256), 
                datetime TIMESTAMP, 
                datetime_utc TIMESTAMP, 
                length FLOAT, 
                range JSON, 
                mz_calibration JSON, 
                tic FLOAT, 
                polarity VARCHAR(1), 
                PRIMARY KEY (sample_file_id), 
                FOREIGN KEY(instrument_function_id) REFERENCES instrument_function (instrument_function_id) ON DELETE SET NULL, 
                UNIQUE (filename)
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
    "user": {
        "columns": {
            "id": ("INTEGER", 1, None, 1),
            "email": ("VARCHAR(320)", 1, None, 0),
            "hashed_password": ("VARCHAR(1024)", 1, None, 0),
            "is_active": ("BOOLEAN", 1, None, 0),
            "is_superuser": ("BOOLEAN", 1, None, 0),
            "is_verified": ("BOOLEAN", 1, None, 0),
            "username": ("VARCHAR(100)", 1, None, 0),
            "role_id": ("INTEGER", 0, None, 0),
            "registered_at": ("TIMESTAMP", 1, None, 0),
        },
        "fks": {
            "role_id": ("role", "role_id", "NO ACTION", "SET NULL"),
        },
        "create_sql": """
            CREATE TABLE user (
                id INTEGER NOT NULL PRIMARY KEY,
                email VARCHAR(320) NOT NULL,
                hashed_password VARCHAR(1024) NOT NULL,
                is_active BOOLEAN NOT NULL,
                is_superuser BOOLEAN NOT NULL,
                is_verified BOOLEAN NOT NULL,
                username VARCHAR(100) NOT NULL,
                role_id INTEGER,
                registered_at TIMESTAMP NOT NULL,
                FOREIGN KEY(role_id) REFERENCES role(role_id) ON DELETE SET NULL,
                UNIQUE (username)
            );
        """,
        "indexes": [
            "ix_user_email ON user (email)",
        ],
    },
    "role": {
        "columns": {
            "role_id": ("INTEGER", 1, None, 1),
            "role_name": ("VARCHAR(50)", 1, None, 0),
            "permissions": ("JSON", 0, None, 0),
        },
        "fks": {},
        "create_sql": """
            CREATE TABLE role (
                role_id INTEGER NOT NULL PRIMARY KEY,
                role_name VARCHAR(50) NOT NULL,
                permissions JSON,
                UNIQUE (role_name)
            );
        """,
    },
    "access_token": {
        "columns": {
            "token": ("VARCHAR(43)", 1, None, 1),
            "user_id": ("INTEGER", 1, None, 0),
            "service_name": ("VARCHAR(50)", 0, None, 0),
            "created_at": ("TIMESTAMP", 1, None, 0),
        },
        "fks": {
            "user_id": ("user", "id", "NO ACTION", "CASCADE"),
        },
        "create_sql": """
            CREATE TABLE access_token (
                token VARCHAR(43) NOT NULL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                service_name VARCHAR(50),
                created_at TIMESTAMP NOT NULL,
                FOREIGN KEY(user_id) REFERENCES user(id) ON DELETE CASCADE
            );
        """,
        "indexes": ["ix_access_token_created_at ON access_token (created_at)"],
    },
}
