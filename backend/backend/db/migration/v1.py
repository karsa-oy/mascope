import nest_asyncio
import os
import sqlite3

# patch asyncio to supported run_until_complete
# when an event loop is already running
nest_asyncio.apply()


def run():
    data_path = os.environ.get('MASCOPE_PRIVATE_DATADIR')

    # STEP 1 - setup new database

    db_path = os.path.join(data_path, 'database', 'mascope.v1.db')
    new_conn = sqlite3.connect(database=db_path)

    with new_conn:
        new_conn.execute("""--sql
            -- workspaces

            CREATE TABLE IF NOT EXISTS workspace (
                workspace_id VARCHAR(16) PRIMARY KEY
                ,workspace_name VARCHAR(256) NOT NULL
                ,workspace_description TEXT
                ,workspace_attributes JSON
            );
        """)
        new_conn.execute("""--sql
            -- ionization mechanisms

            CREATE TABLE IF NOT EXISTS config_mechanism (
                mechanism_id VARCHAR(16) PRIMARY KEY
                ,polarity VARCHAR(1)
                ,mechanism VARCHAR
                ,reagent VARCHAR
            );
        """)
        new_conn.execute("""--sql
            -- samples

            CREATE TABLE IF NOT EXISTS sample_batch (
                sample_batch_id VARCHAR(16) PRIMARY KEY
                ,workspace_id VARCHAR(16) NOT NULL
                    REFERENCES workspace(workspace_id)
                ,sample_batch_name VARCHAR NOT NULL
                ,sample_batch_description TEXT
                ,build_params JSON
                ,filter_params JSON
                ,sample_batch_attributes JSON
                ,calibration_sample_filename VARCHAR(256)
                    REFERENCES sample_file(filename)
            );
        """)
        new_conn.execute("""--sql
            CREATE TABLE IF NOT EXISTS sample_item (
                sample_item_id VARCHAR(16) PRIMARY KEY
                ,sample_batch_id VARCHAR(16) NOT NULL
                    REFERENCES sample_batch(sample_batch_id)
                ,filename VARCHAR(256) NOT NULL
                ,sample_item_name VARCHAR(256) NOT NULL
                ,sample_item_type VARCHAR(64) NOT NULL
                ,sample_item_description TEXT
                ,sample_item_attributes JSON
            );
        """)
        new_conn.execute("""--sql
            CREATE TABLE IF NOT EXISTS sample_file (
                sample_file_id VARCHAR(256) PRIMARY KEY
                ,filename VARCHAR(256) NOT NULL
                ,sample_file_name VARCHAR(256)
                ,sample_file_description TEXT
                ,instrument VARCHAR(64)
                ,datetime TIMESTAMP WITH TIME ZONE
                ,datetime_utc TIMESTAMP
                ,length FLOAT
                ,range JSON
                ,mz_calibration JSON
                ,sample_file_attributes JSON
            );
        """)
        new_conn.execute("""--sql
            CREATE TABLE IF NOT EXISTS attribute_template (
                attribute_template_id VARCHAR(256) PRIMARY KEY
                ,name VARCHAR(256) NOT NULL
                ,type VARCHAR(64)
                ,template JSON
            );
        """)
        new_conn.execute("""--sql
            -- targets

            CREATE TABLE IF NOT EXISTS target_collection (
                target_collection_id VARCHAR(16) PRIMARY KEY
                ,target_collection_name VARCHAR(256) NOT NULL
                ,target_collection_description TEXT
            );
        """)
        new_conn.execute("""--sql
            CREATE TABLE IF NOT EXISTS target_compound (
                target_compound_id VARCHAR(32) PRIMARY KEY
                ,target_compound_name TEXT
                ,target_compound_formula VARCHAR(256) NOT NULL
                ,cas_number VARCHAR(12)
            );
        """)
        new_conn.execute("""--sql
            CREATE TABLE IF NOT EXISTS target_ion (
                target_ion_id VARCHAR(32) PRIMARY KEY
                ,target_compound_id VARCHAR(32) NOT NULL
                    REFERENCES target_compound(target_compound_id)
                ,mechanism_id VARCHAR(16) NOT NULL
                    REFERENCES config_mechanism(mechanism_id)
                ,target_ion_formula VARCHAR(256) NOT NULL
            );
        """)
        new_conn.execute("""--sql
            CREATE TABLE IF NOT EXISTS target_isotope (
                target_isotope_id VARCHAR(32) PRIMARY KEY
                ,target_ion_id VARCHAR(32) NOT NULL
                    REFERENCES target_ion(target_ion_id)
                ,mz FLOAT NOT NULL
                ,relative_abundance FLOAT NOT NULL
                    CHECK (relative_abundance BETWEEN 0 AND 1)
            );
        """)
        new_conn.execute("""--sql
            CREATE TABLE IF NOT EXISTS target_compound_in_target_collection (
                target_compound_id VARCHAR(32)
                    REFERENCES target_compound(target_compound_id)
                ,target_collection_id VARCHAR(16)
                    REFERENCES target_collection(target_collection_id)
            );
        """)
        new_conn.execute("""--sql
            CREATE TABLE IF NOT EXISTS target_collection_in_sample_batch (
                target_collection_id VARCHAR(16) NOT NULL
                    REFERENCES target_collection(target_collection_id)
                ,sample_batch_id VARCHAR(16) NOT NULL
                    REFERENCES sample_batch(sample_batch_id)
                ,PRIMARY KEY
                    (target_collection_id, sample_batch_id)
            );
        """)
        new_conn.execute("""--sql
            -- matches

            CREATE TABLE IF NOT EXISTS match (
                    match_id VARCHAR(32) PRIMARY KEY
                    ,target_isotope_id VARCHAR(16) NOT NULL
                        REFERENCES target_isotope(target_isotope_id)
                    ,sample_item_id VARCHAR(16) NOT NULL
                        REFERENCES sample_item(sample_item_id)
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
        """)

        new_conn.execute("""--sql
            INSERT INTO config_mechanism VALUES
                ( 'SbcztiBgxHg', '-', '-H-',  NULL),
                ( 'fVuWwQ82sJI', '-', '+Br-', 'CH2Br2'),
                ( 'LlqHOw4WWzo', '-', '+NO3-', 'HNO3'),
                ( 'dSiI4x_YoX4', '-', '+(HNO3)NO3-', 'HNO3'),
                ( 'C-6C7BMN2d0', '-',  '+HSO4-', 'NaHSO4'),
                ( '5rm2sP6epAs', '+',  '+H+', NULL),
                ( 'EupOPG6I7bY', '+',  '+Na+',  'NaHSO4'),
                ( 'FkwMOO5RKoU', '+',  '+(C3H6O)H+', 'C3H6O'),
                ( 'gXov_p6BmFY', '+',  '+(C6H10O2)H+', 'C6H10O2'),
                ( 'xeh-m8RpSDI', '+',  '+(C6H15N)H+', 'C6H15N')
        """)
        new_conn.commit()
    new_conn.close()