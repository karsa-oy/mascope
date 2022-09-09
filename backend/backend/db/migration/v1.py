import json
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

    # STEP 1 - setup new database

    db_path = os.path.join(data_path, 'database', 'mascope.v1.db')
    new_conn = sqlite3.connect(database=db_path)

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
        );
    """)
    new_conn.execute("""--sql
        CREATE TABLE IF NOT EXISTS sample_item (
            sample_item_id VARCHAR(16) PRIMARY KEY
            ,sample_batch_id VARCHAR(16) NOT NULL
                REFERENCES sample_batch(sample_batch_id)
            ,filename VARCHAR(256) NOT NULL
            ,sample_item_name VARCHAR(256) NOT NULL
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
    # new_conn.execute("""--sql
    #     -- selection

    #     DROP FUNCTION IF EXISTS selected;

    #     CREATE FUNCTION selected(col, selection, default_value := 0) AS
    #         CASE
    #             WHEN selection >= 2 THEN coalesce(col, default_value)
    #             ELSE default_value
    #         END;
    # """)

    # STEP 2 - load sqlite3 tables into pandas dataframes

    sqlite_path = os.path.join(data_path, 'mascope.db')
    old_conn = sqlite3.connect(sqlite_path)

    print("Transfering workspaces")

    workspace_df = pd.read_sql("""--sql
        SELECT
            id as workspace_id
            ,name as workspace_name
            ,description as workspace_description
            ,attributes as workspace_attributes
        FROM workspaces;
    """,
    old_conn)

    workspace_df.to_sql('workspace', new_conn, if_exists='append', index=False)

    print("Transfering samples and attributes templates")

    sample_batch_df = pd.read_sql("""--sql
        SELECT
            id as sample_batch_id
            ,workspace_id
            ,name as sample_batch_name
            ,description as sample_batch_description
            ,attributes as sample_batch_attributes
        FROM sample_batches;
    """, old_conn)

    num_batches = len(sample_batch_df)
    sample_batch_df = sample_batch_df.assign(
        build_params=[json.dumps({
            'ion_mechanisms': [
                'fVuWwQ82sJI',  # +Br-
                'SbcztiBgxHg',  # -H-
            ]
        })]*num_batches,
        filter_params=[json.dumps({
            # match params
            'mz_tolerance': 10,
            'probable_match_threshold': 0.9,
            'possible_match_threshold': 0.5,
            'isotope_ratio_tolerance': 10,
            'min_isotope_abundance': 0,
            # peak params
            'peak_min_intensity': 1,
            'peak_min_separation': 3,
            'mz_range': None,
            't_range': None,
        })]*num_batches
    )

    sample_batch_df.to_sql('sample_batch', new_conn, if_exists='append', index=False)

    sample_item_df = pd.read_sql("""--sql
        SELECT
            id as sample_item_id
            ,sample_batch_id
            ,filename
            ,title as sample_item_name
            ,description as sample_item_description
            ,attributes as sample_item_attributes
        FROM sample_items;
    """, old_conn)
    sample_item_df.to_sql('sample_item', new_conn, if_exists='append', index=False)

    sample_file_df = pd.read_sql("""--sql
        SELECT
            id as sample_file_id
            ,filename
            ,title as sample_file_name
            ,description as sample_file_description
            ,instrument
            ,datetime
            ,datetime_utc
            ,length
            ,range
            ,attributes as sample_file_attributes
        FROM sample_files;
    """, old_conn)
    sample_file_df.to_sql('sample_file', new_conn, if_exists='append', index=False)

    attribute_template_df = pd.read_sql("""--sql
        SELECT
            id as attribute_template_id
            ,name
            ,type
            ,template
        FROM attribute_templates;
    """, old_conn)
    attribute_template_df.to_sql('attribute_template', new_conn, if_exists='append', index=False)

    print("Transfering targets and recreating ionization mechanisms")

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

    target_collection_df = pd.read_sql("""--sql
        SELECT
            id as target_collection_id
            ,name as target_collection_name
            ,description as target_collection_description
        FROM target_collections;
    """, old_conn)
    target_collection_df.to_sql('target_collection', new_conn, if_exists='append', index=False)

    target_compound_df = pd.read_sql("""--sql
        SELECT
            id as target_compound_id
            ,name as target_compound_name
            ,formula as target_compound_formula
            ,cas_number
        FROM target_compounds;
    """, old_conn)
    target_compound_df.to_sql('target_compound', new_conn, if_exists='append', index=False)

    target_ion_df = pd.read_sql("""--sql
        SELECT
            id as target_ion_id
            ,target_compound_id
            ,mechanism_id
            ,formula as target_ion_formula
        FROM target_ions;
    """, old_conn)

    target_ion_df.to_sql('target_ion', new_conn, if_exists='append', index=False)

    target_isotope_df = pd.read_sql("""--sql
        SELECT
            id as target_isotope_id
            ,target_ion_id
            ,mz
            ,relative_abundance
        FROM target_isotopes;
    """, old_conn)
    target_isotope_df.to_sql('target_isotope', new_conn, if_exists='append', index=False)

    target_compound_in_target_collection_df = pd.read_sql("""--sql
        SELECT
            target_compound_id
            ,target_collection_id
        FROM target_compound_in_target_collection;
    """, old_conn)
    target_compound_in_target_collection_df.to_sql('target_compound_in_target_collection', new_conn, if_exists='append', index=False)

    target_collection_in_sample_batch_df = pd.read_sql("""--sql
        SELECT
            target_collection_id
            ,sample_batch_id
        FROM target_collection_in_sample_batch;
    """, old_conn)
    target_collection_in_sample_batch_df.to_sql('target_collection_in_sample_batch', new_conn, if_exists='append', index=False)

    # compute matches

    print('Computing matches for all sample batches')
    asyncio.get_event_loop().run_until_complete(
        compute_all_matches(new_conn)
    )


async def compute_all_matches(new_conn):
    cur = new_conn.cursor()
    # get sample batches
    sample_batches = pd.read_sql("""--sql
        SELECT * FROM sample_batch
    """, new_conn).to_dict('records')

    for sample_batch in sample_batches:
        print(f"Matching {sample_batch['sample_batch_name']}")
        # get ionization mechanisms
        build_params = json.loads(
            sample_batch['build_params']
        )
        ion_mechanism_df = pd.DataFrame.from_dict({
            'mechanism_id': build_params['ion_mechanisms']
        })
        mechanism_ids = ion_mechanism_df['mechanism_id'].tolist()
        mechanism_id_refs = ','.join('?'*len(mechanism_ids))
        # load target isotopes in the batch
        target_isotope_df = pd.read_sql(f"""--sql
            SELECT
                target_isotope.*
            FROM
                target_collection_in_sample_batch batch
                NATURAL JOIN target_compound_in_target_collection
                NATURAL JOIN target_ion
                NATURAL JOIN target_isotope
            WHERE
                sample_batch_id == '{sample_batch['sample_batch_id']}'
                AND mechanism_id IN ({mechanism_id_refs})
            """,
            new_conn,
            params=mechanism_ids
            )
        
        # fetch item ids
        sample_item_ids = pd.read_sql("""
            SELECT sample_item_id FROM sample_item
            WHERE sample_batch_id == ?
            """,
            new_conn,
            params=[sample_batch['sample_batch_id']]
            )['sample_item_id'].tolist()
        # concurrently perform matching
        match_item_tasks = []
        for sample_item_id in sample_item_ids:
            match_item_tasks.append(
                asyncio.create_task(
                    match_item_compute(
                        new_conn, 
                        sample_item_id,
                        target_isotope_df
                    )
                )
            )
        await asyncio.gather(*match_item_tasks)


async def match_item_compute(
        new_conn,
        sample_item_id,
        target_isotope_df
        ):

    mz_tolerance = 0.5

    # Note:
    #   Matching is done on isotope-level. Ion, compound
    #   and collection level matches are aggregated from
    #   isotope-level matches on read; see the frontend
    #   batch store module for this aggregation.

    # get sample item
    [sample_item] = pd.read_sql("""--sql
        SELECT * FROM sample_item
        WHERE sample_item_id == ?
        """,
        new_conn,
        params=[sample_item_id]
        ).to_dict('records')
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

    match_isotope_df = match_isotope_df[[
        "match_id"
        ,"target_isotope_id"
        ,"sample_item_id"
        ,"sample_peak_id"
        ,"sample_peak_mz"
        ,"sample_peak_height"
        ,"sample_peak_height_relative"
        ,"sample_peak_tof"
        ,"match_abundance_error"
        ,"match_mz_error"
        ,"match_score"
    ]]
    # save to database
    match_isotope_df.to_sql('match', new_conn, if_exists='append', index=False)

