import asyncio
import nest_asyncio
import os
import pandas as pd
import sqlite3

from datetime import datetime

# patch asyncio to supported run_until_complete
# when an event loop is already running
nest_asyncio.apply()


def run():
    data_path = os.environ.get("MASCOPE_PRIVATE_DATABASE_DIR")

    # STEP 1 - setup new database

    db_path = os.path.join(data_path, "mascope.v2.db")
    new_conn = sqlite3.connect(database=db_path)
    with new_conn:
        # Add datetime created and modified
        # Remove workspace_attributes
        new_conn.execute(
            """--sql
            -- workspaces

            CREATE TABLE workspace (
                workspace_id VARCHAR(16) PRIMARY KEY
                ,workspace_name VARCHAR(256) NOT NULL
                ,workspace_description TEXT
                ,workspace_utc_created TIMESTAMP
                ,workspace_utc_modified TIMESTAMP
            );
        """
        )
        new_conn.execute(
            """--sql
            -- ionization mechanisms

            CREATE TABLE ionization_mechanism (
                ionization_mechanism_id VARCHAR(16) PRIMARY KEY
                ,ionization_mechanism_polarity VARCHAR(1)
                ,ionization_mechanism VARCHAR
                ,reagent VARCHAR
            );
        """
        )

        # Add datetime created and modified
        # Remove sample_batch_attributes
        new_conn.execute(
            """--sql
            -- samples

            CREATE TABLE sample_batch (
                sample_batch_id VARCHAR(16) PRIMARY KEY
                ,workspace_id VARCHAR(16) NOT NULL
                    REFERENCES workspace(workspace_id) ON DELETE CASCADE
                ,sample_batch_name VARCHAR NOT NULL
                ,sample_batch_description TEXT
                ,build_params JSON
                ,filter_params JSON
                ,sample_batch_utc_created TIMESTAMP
                ,sample_batch_utc_modified TIMESTAMP
            );
        """
        )

        # Add datetime created and modified
        # Remove sample_item_description
        new_conn.execute(
            """--sql
            CREATE TABLE sample_item (
                sample_item_id VARCHAR(16) PRIMARY KEY
                ,sample_batch_id VARCHAR(16) NOT NULL
                    REFERENCES sample_batch(sample_batch_id) ON DELETE CASCADE
                ,filename VARCHAR(256) NOT NULL
                ,sample_item_name VARCHAR(256) NOT NULL
                ,sample_item_type VARCHAR(64) NOT NULL
                ,sample_item_attributes JSON
                ,sample_item_utc_created TIMESTAMP
                ,sample_item_utc_modified TIMESTAMP
            );
        """
        )

        # Remove sample_file_attributes, sample_file_name and sample_file_description
        new_conn.execute(
            """--sql
            CREATE TABLE sample_file (
                sample_file_id VARCHAR(256) PRIMARY KEY
                ,filename VARCHAR(256) NOT NULL
                ,instrument VARCHAR(64)
                ,datetime TIMESTAMP WITH TIME ZONE
                ,datetime_utc TIMESTAMP
                ,length FLOAT
                ,range JSON
                ,mz_calibration JSON
            );
        """
        )

        new_conn.execute(
            """--sql
            CREATE TABLE attribute_template (
                attribute_template_id VARCHAR(256) PRIMARY KEY
                ,name VARCHAR(256) NOT NULL
                ,type VARCHAR(64)
                ,template JSON
            );
        """
        )

        new_conn.execute(
            """--sql
            -- targets
            CREATE TABLE target_collection (
                target_collection_id VARCHAR(16) PRIMARY KEY
                ,target_collection_name VARCHAR(256) NOT NULL
                ,target_collection_description TEXT
            );
        """
        )

        new_conn.execute(
            """--sql
            CREATE TABLE target_compound (
                target_compound_id VARCHAR(32) PRIMARY KEY
                ,target_compound_name TEXT
                ,target_compound_formula VARCHAR(256) NOT NULL
                ,cas_number VARCHAR(12)
            );
        """
        )

        # Rename mechanism_id -> ionization_mechanism_id
        new_conn.execute(
            """--sql
            CREATE TABLE target_ion (
                target_ion_id VARCHAR(32) PRIMARY KEY
                ,target_compound_id VARCHAR(32) NOT NULL
                    REFERENCES target_compound(target_compound_id) ON DELETE CASCADE
                ,ionization_mechanism_id VARCHAR(16) NOT NULL
                    REFERENCES ionization_mechanism(ionization_mechanism_id)
                ,target_ion_formula VARCHAR(256) NOT NULL
            );
        """
        )
        new_conn.execute(
            """--sql
            CREATE TABLE target_isotope (
                target_isotope_id VARCHAR(32) PRIMARY KEY
                ,target_ion_id VARCHAR(32) NOT NULL
                    REFERENCES target_ion(target_ion_id) ON DELETE CASCADE
                ,mz FLOAT NOT NULL
                ,relative_abundance FLOAT NOT NULL
                    CHECK (relative_abundance BETWEEN 0 AND 1)
            );
        """
        )
        new_conn.execute(
            """--sql
            CREATE TABLE target_compound_in_target_collection (
                target_compound_id VARCHAR(32)
                    REFERENCES target_compound(target_compound_id)
                ,target_collection_id VARCHAR(16)
                    REFERENCES target_collection(target_collection_id) ON DELETE CASCADE
            );
        """
        )
        new_conn.execute(
            """--sql
            CREATE TABLE target_collection_in_sample_batch (
                target_collection_id VARCHAR(16) NOT NULL
                    REFERENCES target_collection(target_collection_id)
                ,sample_batch_id VARCHAR(16) NOT NULL
                    REFERENCES sample_batch(sample_batch_id) ON DELETE CASCADE
                ,PRIMARY KEY
                    (target_collection_id, sample_batch_id)
            );
        """
        )
        new_conn.execute(
            """--sql
            -- matches

            CREATE TABLE match (
                    match_id VARCHAR(32) PRIMARY KEY
                    ,target_isotope_id VARCHAR(16) NOT NULL
                        REFERENCES target_isotope(target_isotope_id) ON DELETE CASCADE
                    ,sample_item_id VARCHAR(16) NOT NULL
                        REFERENCES sample_item(sample_item_id) ON DELETE CASCADE
                    ,sample_peak_id INT NOT NULL
                    ,sample_peak_mz FLOAT NOT NULL
                    ,sample_peak_height FLOAT NOT NULL
                    ,sample_peak_height_relative FLOAT NOT NULL
                    ,sample_peak_tof FLOAT NOT NULL
                    ,match_abundance_error FLOAT NOT NULL
                    ,match_mz_error FLOAT NOT NULL
                    ,match_score FLOAT NOT NULL
                        CHECK (match_score BETWEEN 0 AND 1)
            );
        """
        )
        # STEP 2 - load v1 tables into pandas dataframes and write to v2
        sqlite_path = os.path.join(data_path, "mascope.v1.db")
        old_conn = sqlite3.connect(sqlite_path)
        with old_conn:
            print("Transfering workspaces")

            workspace_df = pd.read_sql(
                """--sql
                SELECT
                    workspace_id
                    ,workspace_name
                    ,workspace_description
                FROM workspace;
            """,
                old_conn,
            )

            workspace_df["workspace_utc_created"] = [datetime.now().isoformat()] * len(
                workspace_df
            )
            workspace_df["workspace_utc_modified"] = [datetime.now().isoformat()] * len(
                workspace_df
            )

            workspace_df.to_sql("workspace", new_conn, if_exists="append", index=False)

            print("Transfering samples and attributes templates")

            sample_batch_df = pd.read_sql(
                """--sql
                SELECT
                    sample_batch_id,
                    workspace_id,
                    sample_batch_name,
                    sample_batch_description,
                    build_params,
                    filter_params
                FROM sample_batch;
            """,
                old_conn,
            )

            sample_batch_df["sample_batch_utc_created"] = [
                datetime.now().isoformat()
            ] * len(sample_batch_df)
            sample_batch_df["sample_batch_utc_modified"] = [
                datetime.now().isoformat()
            ] * len(sample_batch_df)

            sample_batch_df.to_sql(
                "sample_batch", new_conn, if_exists="append", index=False
            )

            sample_item_df = pd.read_sql(
                """--sql
                SELECT
                    sample_item_id
                    ,sample_batch_id
                    ,filename
                    ,sample_item_name
                    ,sample_item_type
                    ,sample_item_attributes
                FROM sample_item;
            """,
                old_conn,
            )

            sample_item_df["sample_item_utc_created"] = [
                datetime.now().isoformat()
            ] * len(sample_item_df)
            sample_item_df["sample_item_utc_modified"] = [
                datetime.now().isoformat()
            ] * len(sample_item_df)

            sample_item_df.to_sql(
                "sample_item", new_conn, if_exists="append", index=False
            )

            sample_file_df = pd.read_sql(
                """--sql
                SELECT
                    sample_file_id
                    ,filename
                    ,instrument
                    ,datetime
                    ,datetime_utc
                    ,length
                    ,range
                    ,mz_calibration
                FROM sample_file;
            """,
                old_conn,
            )
            sample_file_df.to_sql(
                "sample_file", new_conn, if_exists="append", index=False
            )

            attribute_template_df = pd.read_sql(
                """--sql
                SELECT
                    attribute_template_id
                    ,name
                    ,type
                    ,template
                FROM attribute_template;
            """,
                old_conn,
            )
            attribute_template_df.to_sql(
                "attribute_template", new_conn, if_exists="append", index=False
            )

            print("Transfering targets and ionization mechanisms")

            # Rename mechanism_id -> ionization_mechanism_id,
            # polarity -> ionization_mechanism_polarity,
            # mechanism -> ionization_mechanism
            ionization_mechanism_df = pd.read_sql(
                """--sql
                SELECT
                    mechanism_id AS ionization_mechanism_id
                    ,polarity AS ionization_mechanism_polarity
                    ,mechanism AS ionization_mechanism
                    ,reagent
                FROM config_mechanism;
            """,
                old_conn,
            )
            ionization_mechanism_df.to_sql(
                "ionization_mechanism", new_conn, if_exists="append", index=False
            )

            target_collection_df = pd.read_sql(
                """--sql
                SELECT
                    target_collection_id
                    ,target_collection_name
                    ,target_collection_description
                FROM target_collection;
            """,
                old_conn,
            )
            target_collection_df.to_sql(
                "target_collection", new_conn, if_exists="append", index=False
            )

            target_compound_df = pd.read_sql(
                """--sql
                SELECT
                    target_compound_id
                    ,target_compound_name
                    ,target_compound_formula
                    ,cas_number
                FROM target_compound;
            """,
                old_conn,
            )
            target_compound_df.to_sql(
                "target_compound", new_conn, if_exists="append", index=False
            )

            target_ion_df = pd.read_sql(
                """--sql
                SELECT
                    target_ion_id
                    ,target_compound_id
                    ,mechanism_id AS ionization_mechanism_id
                    ,target_ion_formula
                FROM target_ion;
            """,
                old_conn,
            )

            target_ion_df.to_sql(
                "target_ion", new_conn, if_exists="append", index=False
            )

            target_isotope_df = pd.read_sql(
                """--sql
                SELECT
                    target_isotope_id
                    ,target_ion_id
                    ,mz
                    ,relative_abundance
                FROM target_isotope;
            """,
                old_conn,
            )
            target_isotope_df.to_sql(
                "target_isotope", new_conn, if_exists="append", index=False
            )

            target_compound_in_target_collection_df = pd.read_sql(
                """--sql
                SELECT
                    target_compound_id
                    ,target_collection_id
                FROM target_compound_in_target_collection;
            """,
                old_conn,
            )
            target_compound_in_target_collection_df.to_sql(
                "target_compound_in_target_collection",
                new_conn,
                if_exists="append",
                index=False,
            )

            target_collection_in_sample_batch_df = pd.read_sql(
                """--sql
                SELECT
                    target_collection_id
                    ,sample_batch_id
                FROM target_collection_in_sample_batch;
            """,
                old_conn,
            )
            target_collection_in_sample_batch_df.to_sql(
                "target_collection_in_sample_batch",
                new_conn,
                if_exists="append",
                index=False,
            )

            print("Transfering matches")

            match_df = pd.read_sql(
                """--sql
                SELECT
                    *
                FROM match;
            """,
                old_conn,
            )

            # Drop dangling matches (matching sample item missing)
            match_sample_item_ids = pd.unique(match_df["sample_item_id"]).tolist()
            for sample_item_id in match_sample_item_ids:
                if sample_item_id not in sample_item_df["sample_item_id"].values:
                    match_df.drop(
                        match_df[match_df.sample_item_id == sample_item_id].index,
                        inplace=True,
                    )

            match_df.to_sql("match", new_conn, if_exists="append", index=False)
    new_conn.commit()
    new_conn.close()
    old_conn.close()
