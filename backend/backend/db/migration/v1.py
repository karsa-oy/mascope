import duckdb
import sqlite3
import pandas as pd
import os

import numpy as np
import asyncio
import nest_asyncio

from backend.db import gen_id
from backend.lib.peak import detect_peaks, get_peaks
from backend.lib.chemistry import match_mz
import backend.lib.hack as hack

from backend.lib.file import load_file


# patch asyncio to supported run_until_complete
# when an event loop is already running
nest_asyncio.apply()


def run():
    data_path = os.environ.get('MASCOPE_PRIVATE_DATADIR')

    # STEP 1 - setup new duckdb database

    duckdb_path = os.path.join(data_path, 'database', 'mascope.v1.duckdb')
    duckdb_con = duckdb.connect(database=duckdb_path)

    duckdb_con.execute("""--sql
        -- json extension

        INSTALL 'json';
        LOAD 'json';

        -- workspaces

        CREATE TABLE IF NOT EXISTS workspace (
            workspace_id VARCHAR(16) PRIMARY KEY
            ,name VARCHAR(256) NOT NULL
            ,description TEXT
            ,attributes JSON
        );

        -- ionization mechanisms

        CREATE TABLE IF NOT EXISTS config_mechanism (
            mechanism_id VARCHAR(16) PRIMARY KEY
            ,polarity VARCHAR(1)
            ,mechanism VARCHAR
            ,reagent VARCHAR
        );

        -- samples

        CREATE TABLE IF NOT EXISTS sample_batch (
            sample_batch_id VARCHAR(16) PRIMARY KEY
            ,workspace_id VARCHAR(16) NOT NULL
                REFERENCES workspace(workspace_id)
            ,name VARCHAR NOT NULL
            ,description TEXT
            ,build_params JSON
            ,filter_params JSON
            ,attributes JSON
        );

        CREATE TABLE IF NOT EXISTS sample_item (
            sample_item_id VARCHAR(16) PRIMARY KEY
            ,sample_batch_id VARCHAR(16) NOT NULL
                REFERENCES sample_batch(sample_batch_id)
            ,filename VARCHAR(256) NOT NULL
            ,title VARCHAR(256) NOT NULL
            ,description TEXT
            ,attributes JSON
        );

        CREATE TABLE IF NOT EXISTS sample_file (
            sample_file_id VARCHAR(256) PRIMARY KEY
            ,filename VARCHAR(256) NOT NULL
            ,title VARCHAR(256)
            ,description TEXT
            ,instrument VARCHAR(64)
            ,datetime TIMESTAMP WITH TIME ZONE
            ,datetime_utc TIMESTAMP
            ,length FLOAT
            ,range JSON
            ,mz_calibration JSON
            ,attributes JSON
        );

        CREATE TABLE IF NOT EXISTS attribute_template (
            attribute_template_id VARCHAR(256) PRIMARY KEY
            ,name VARCHAR(256) NOT NULL
            ,type VARCHAR(64)
            ,template JSON
        );

        -- targets

        CREATE TABLE IF NOT EXISTS target_collection (
            target_collection_id VARCHAR(16) PRIMARY KEY
            ,name VARCHAR(256) NOT NULL
            ,description TEXT
        );

        CREATE TABLE IF NOT EXISTS target_compound (
            target_compound_id VARCHAR(32) PRIMARY KEY
            ,name TEXT
            ,formula VARCHAR(256) NOT NULL
            ,cas_number VARCHAR(12)
        );

        CREATE TABLE IF NOT EXISTS target_ion (
            target_ion_id VARCHAR(32) PRIMARY KEY
            ,target_compound_id VARCHAR(32) NOT NULL
                REFERENCES target_compound(target_compound_id)
            ,mechanism_id VARCHAR(16) NOT NULL
                REFERENCES config_mechanism(mechanism_id)
            ,formula VARCHAR(256) NOT NULL
        );

        CREATE TABLE IF NOT EXISTS target_isotope (
            target_isotope_id VARCHAR(32) PRIMARY KEY
            ,target_ion_id VARCHAR(32) NOT NULL
                REFERENCES target_ion(target_ion_id)
            ,mz FLOAT NOT NULL
            ,relative_abundance FLOAT NOT NULL
                CHECK (relative_abundance BETWEEN 0 AND 1)
        );

        CREATE TABLE IF NOT EXISTS target_compound_in_target_collection (
            target_compound_id VARCHAR(32)
                REFERENCES target_compound(target_compound_id)
            ,target_collection_id VARCHAR(16)
                REFERENCES target_collection(target_collection_id)
        );

        CREATE TABLE IF NOT EXISTS target_collection_in_sample_batch (
            target_collection_id VARCHAR(16) NOT NULL
                REFERENCES target_collection(target_collection_id)
            ,sample_batch_id VARCHAR(16) NOT NULL
                REFERENCES sample_batch(sample_batch_id)
            ,PRIMARY KEY
                (target_collection_id, sample_batch_id)
        );

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

    # STEP 2 - load sqlite3 tables into pandas dataframes

    sqlite_path = os.path.join(data_path, 'mascope.db')
    sqlite_con = sqlite3.connect(sqlite_path)

    print("Transfering data from SQLite to DuckDB")

    print("Transfering workspaces")

    workspace_df = pd.read_sql("""--sql
        SELECT
            id as workspace_id
            ,name
            ,description
            ,attributes
        FROM workspaces;
    """, sqlite_con)

    duckdb_con.execute("""--sql
        INSERT INTO workspace (
            workspace_id
            ,name
            ,description
            ,attributes
        )
        (SELECT * FROM workspace_df)
    """)

    print("Transfering samples and attributes templates")

    sample_batch_df = pd.read_sql("""--sql
        SELECT
            id as sample_batch_id
            ,workspace_id
            ,name
            ,description
            ,attributes
        FROM sample_batches;
    """, sqlite_con)

    num_batches = len(sample_batch_df)
    sample_batch_df = sample_batch_df.assign(
        build_params=[{
            'ion_mechanisms': [
                'fVuWwQ82sJI',  # +Br-
                'SbcztiBgxHg',  # -H-
            ]
        }]*num_batches,
        filter_params=[{
            # match params
            'mz_tolerance': 10,
            'probable_match_threshold': 0.9,
            'possible_match_threshold': 0.5,
            'iso_ratio_tolerance': 10,  # %
            # peak params
            'peak_min_intensity': 1,
            'peak_min_separation': 3,
            'mz_range': None,
            't_range': None,
        }]*num_batches
    )

    duckdb_con.execute("""--sql
        INSERT INTO sample_batch (
            sample_batch_id
            ,workspace_id
            ,name
            ,description
            ,attributes
            ,build_params
            ,filter_params
        )
        (SELECT * FROM sample_batch_df)
    """)

    sample_item_df = pd.read_sql("""--sql
        SELECT
            id as sample_item_id
            ,sample_batch_id
            ,filename
            ,title
            ,description
            ,attributes
        FROM sample_items;
    """, sqlite_con)

    duckdb_con.execute("""--sql
        INSERT INTO sample_item (
            sample_item_id
            ,sample_batch_id
            ,filename
            ,title
            ,description
            ,attributes
        )
        (SELECT * FROM sample_item_df)
    """)

    sample_file_df = pd.read_sql("""--sql
        SELECT
            id as sample_file_id
            ,filename
            ,title
            ,description
            ,instrument
            ,datetime
            ,datetime_utc
            ,length
            ,range
            ,attributes
        FROM sample_files;
    """, sqlite_con)

    duckdb_con.execute("""--sql
        INSERT INTO sample_file (
            sample_file_id
            ,filename
            ,title
            ,description
            ,instrument
            ,datetime
            ,datetime_utc
            ,length
            ,range
            ,attributes
        )
        (SELECT * FROM sample_file_df)
    """)

    attribute_template_df = pd.read_sql("""--sql
        SELECT
            id as attribute_template_id
            ,name
            ,type
            ,template
        FROM attribute_templates;
    """, sqlite_con)

    duckdb_con.execute("""--sql
        INSERT INTO attribute_template (
            attribute_template_id
            ,name
            ,type
            ,template
        )
        (SELECT * FROM attribute_template_df)
    """)

    print("Transfering targets and recreating ionization mechanisms")

    duckdb_con.execute("""--sql
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

    target_collection_df = pd.read_sql("""--sql
        SELECT
            id as target_collection_id
            ,name
            ,description
        FROM target_collections;
    """, sqlite_con)

    duckdb_con.execute("""--sql
        INSERT INTO target_collection (
            target_collection_id
            ,name
            ,description
        )
        (SELECT * FROM target_collection_df)
    """)

    target_compound_df = pd.read_sql("""--sql
        SELECT
            id as target_compound_id
            ,name
            ,formula
            ,cas_number
        FROM target_compounds;
    """, sqlite_con)

    duckdb_con.execute("""--sql
        INSERT INTO target_compound (
            target_compound_id
            ,name
            ,formula
            ,cas_number
        )
        (SELECT * FROM target_compound_df)
    """)

    target_ion_df = pd.read_sql("""--sql
        SELECT
            id as target_ion_id
            ,target_compound_id
            ,mechanism_id
            ,formula
        FROM target_ions;
    """, sqlite_con)

    duckdb_con.execute("""--sql
        INSERT INTO target_ion (
            target_ion_id
            ,target_compound_id
            ,mechanism_id
            ,formula
        )
        (SELECT * FROM target_ion_df)
    """)

    target_isotope_df = pd.read_sql("""--sql
        SELECT
            id as target_isotope_id
            ,target_ion_id
            ,mz
            ,relative_abundance
        FROM target_isotopes;
    """, sqlite_con)

    duckdb_con.execute("""--sql
        INSERT INTO target_isotope (
            target_isotope_id
            ,target_ion_id
            ,mz
            ,relative_abundance
        )
        (SELECT * FROM target_isotope_df)
    """)

    target_compound_in_target_collection_df = pd.read_sql("""--sql
        SELECT
            target_compound_id
            ,target_collection_id
        FROM target_compound_in_target_collection;
    """, sqlite_con)

    duckdb_con.execute("""--sql
        INSERT INTO target_compound_in_target_collection (
            target_compound_id
            ,target_collection_id
        )
        (SELECT * FROM target_compound_in_target_collection_df)
    """)

    target_collection_in_sample_batch_df = pd.read_sql("""--sql
        SELECT
            target_collection_id
            ,sample_batch_id
        FROM target_collection_in_sample_batch;
    """, sqlite_con)

    duckdb_con.execute("""--sql
        INSERT INTO target_collection_in_sample_batch (
            target_collection_id
            ,sample_batch_id
        )
        (SELECT * FROM target_collection_in_sample_batch_df)
    """)

    # compute matches

    print('Computing matches for all sample batches')
    asyncio.get_event_loop().run_until_complete(
        compute_all_matches(duckdb_con)
    )


async def compute_all_matches(duckdb_con):
    cur = duckdb_con.cursor()
    # get sample batches
    sample_batches = duckdb_con.execute("""--sql
        SELECT * FROM sample_batch
    """).fetchdf().to_dict('records')

    for sample_batch in sample_batches:
        print(f"Matching {sample_batch['name']}")
        # get ionization mechanisms
        build_params = hack.load_json_field(
            sample_batch['build_params']
        )
        ion_mechanism_df = pd.DataFrame.from_dict({
            'mechanism_id': build_params['ion_mechanisms']
        })

        # load target isotopes in the batch
        target_isotope_df = cur.execute(f"""--sql
            SELECT
                target_isotope.*
            FROM
                target_collection_in_sample_batch batch
                NATURAL JOIN target_compound_in_target_collection
                NATURAL JOIN target_ion
                NATURAL JOIN target_isotope
            WHERE
                sample_batch_id == '{sample_batch['sample_batch_id']}'
                AND mechanism_id IN (
                    SELECT mechanism_id FROM ion_mechanism_df
                )
        """).fetchdf()

        # fetch item ids
        sample_item_ids = duckdb_con.execute("""
            SELECT sample_item_id FROM sample_item
            WHERE sample_batch_id == ?
        """, [
            sample_batch['sample_batch_id']
        ]).fetchdf()['sample_item_id'].tolist()

        # concurrently perform matching
        match_item_tasks = []
        for sample_item_id in sample_item_ids:
            match_item_tasks.append(
                asyncio.create_task(
                    match_item_compute(
                        duckdb_con,
                        sample_item_id,
                        target_isotope_df
                    )
                )
            )
        await asyncio.gather(*match_item_tasks)


async def match_item_compute(
        duckdb_con,
        sample_item_id,
        target_isotope_df
        ):

    cur = duckdb_con.cursor()

    mz_tolerance = 0.5

    # Note:
    #   Matching is done on isotope-level. Ion, compound
    #   and collection level matches are aggregated from
    #   isotope-level matches on read; see the frontend
    #   batch store module for this aggregation.

    # get sample item
    [sample_item] = cur.execute("""--sql
        SELECT * FROM sample_item
        WHERE sample_item_id == ?
    """, [
        sample_item_id
    ]).fetchdf().to_dict('records')
    filename = sample_item['filename']

    ######################
    # STEP 1 - Get peaks #
    ######################

    # File not in cache, load
    print("Loading file: %s" % filename)
    cache_item = load_file(filename, vars=['peaks'])

    if 'peaks' not in cache_item:
        # Find peaks and write to file
        cache_item = detect_peaks(cache_item)

    peaks = get_peaks(cache_item)

    print(f"Matching {filename}")

    #########################
    # STEP 2 - Prepare data #
    #########################

    # init match df from target isotopes
    match_isotope_df = (
        target_isotope_df.copy()
        .assign(
            match_id=np.nan,
            sample_item_id=sample_item['sample_item_id'],
            sample_peak_id=np.nan,
            sample_peak_mz=np.nan,
            sample_peak_height=np.nan,
            sample_peak_height_relative=np.nan,
            match_abundance_error=np.nan,
            match_mz_error=np.nan,
            match_score=np.nan,
        )
    )

    # parse peak data
    peak_mzs = peaks.mz.values
    peak_heights = peaks.sum(dim='time').values
    peak_tofs = peaks.tof.values
    peak_sorting = np.argsort(peak_mzs)

    #############################
    # STEP 3 - Perform matching #
    #############################

    def match(row):
        target_mz = row.mz
        match_indeces, match_mzs = match_mz(
            target_mz,
            peak_mzs[peak_sorting],
            tolerance=mz_tolerance
        )
        for match_index in match_indeces:
            # get match peak
            peak_index = peak_sorting[match_index]
            peak_mz = peak_mzs[peak_index]
            peak_height = peak_heights[peak_index]
            # check current betch match
            best_match = row.sample_peak_id
            if not np.isnan(best_match):
                prev_mz_err = np.abs(row.sample_peak_mz - target_mz)
                new_mz_err = np.abs(peak_mz - target_mz)
                if new_mz_err > prev_mz_err:
                    continue
            # save match
            row['match_id'] = gen_id(length=32)
            row['sample_peak_id'] = peak_index
            row['sample_peak_mz'] = peak_mz
            row['sample_peak_tof'] = peak_tofs[int(peak_index)]
            row['sample_peak_height'] = peak_height
        return row

    match_isotope_df = (
        match_isotope_df
        .apply(match, axis=1)
        .dropna(subset=['sample_peak_mz'])
        .reset_index()
    )

    ##################################
    # STEP 4 - Calculate match stats #
    ##################################

    # calculate isotope ratios

    # sum matched sample peak heights for each ion
    ion_level_peak_sums = (
        match_isotope_df
        .groupby(['target_ion_id'], as_index=False)['sample_peak_height']
        .sum()
    )
    # join sums back to the isotope level
    isotope_level_peak_sums = pd.merge(
        match_isotope_df,
        ion_level_peak_sums.rename(
            columns={'sample_peak_height': 'sample_peak_height_sum'}
        ),
        on=['target_ion_id'], how='left'
    )

    # compute relative peak heights
    match_isotope_df.loc[:, 'sample_peak_height_relative'] = (
        match_isotope_df['sample_peak_height']
        / isotope_level_peak_sums['sample_peak_height_sum']
    )
    # calculate isotope ratio errors
    match_isotope_df.loc[:, 'match_abundance_error'] = (
        match_isotope_df['relative_abundance']
        * (
            match_isotope_df['sample_peak_height_relative']
            - match_isotope_df['relative_abundance']
        )
    )

    # calculate mz errors
    match_isotope_df.loc[:, 'match_mz_error'] = (
        1e6 * (match_isotope_df['sample_peak_mz'] - match_isotope_df['mz'])
        / match_isotope_df['sample_peak_mz']
    )

    def score(row):
        row['match_score'] = (
            (1 - abs(row.match_abundance_error))
            * max(0, (1 - 1e-2 * abs(row.match_mz_error)))
        )
        return row

    match_isotope_df = match_isotope_df.apply(
        score,
        axis=1,
        result_type='broadcast'
    )

    print(match_isotope_df.iloc[0])

    # save to database
    cur.execute("""--sql
        INSERT INTO match (
            SELECT
                match_id
                ,target_isotope_id
                ,sample_item_id
                ,sample_peak_id
                ,sample_peak_mz
                ,sample_peak_height
                ,sample_peak_height_relative
                ,sample_peak_tof
                ,match_abundance_error
                ,match_mz_error
                ,match_score
            FROM match_isotope_df
        );
    """)

