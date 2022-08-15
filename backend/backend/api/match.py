import numpy as np
import pandas as pd
import asyncio

from backend.db.conn import init_cursor
from backend.db.id import gen_ids
from backend.lib.peak import detect_peaks, get_peaks
from backend.lib.struct import LRUDict
from backend.lib.chemistry import match_mz

from backend.lib.file import load_file

from backend.server import sio

cur = init_cursor()

# File cache
cache = LRUDict(10)

# Note:
#   The match API performs computations on a batch level
#   not endpoints are provided for creating / removing
#   match items individually.


@sio.event(namespace='/api')
async def match_batch_compute(sid, sample_batch_id):

    # clear previous matches
    match_batch_remove(sid, sample_batch_id)

    # get sample batch
    [sample_batch] = cur.execute("""--sql
        SELECT * FROM sample_batch
        WHERE sample_batch_id == ?
    """, [
        sample_batch_id
    ]).fetchdf().to_dict('records')

    # get ionization mechanisms
    ion_mechanisms = sample_batch['build_params']['ion_mechanisms']
    ion_mechanisms_df = pd.DataFrame.from_dict({
        'mechanism_id': ion_mechanisms
    })

    # load target isotopes in the batch
    target_isotope_df = cur.execute(f"""
        SELECT
            target_isotope.*
        FROM
            target_collection_in_sample_batch batch
            NATURAL JOIN target_compound_in_target_collection
            NATURAL JOIN target_ion
            NATURAL JOIN target_isotope
        WHERE
            sample_batch_id == '{sample_batch_id}'
            AND mechanism_id IN (
                SELECT mechanism_id FROM ion_mechanism_df
            )
    """).fetchdf()

    # fetch item ids
    sample_item_ids = cur.execute("""
        SELECT sample_item_id FROM sample_item
        WHERE sample_batch_id == ?
    """, [
        sample_batch_id
    ]).fetchdf()['sample_item_id'].tolist()

    # concurrently perform matching
    match_item_tasks = []
    for sample_item_id in sample_item_ids:
        match_item_tasks.append(
            asyncio.create_task(
                match_item_compute(
                    sample_item_id,
                    target_isotope_df,
                )
            )
        )
    await asyncio.gather(*match_item_tasks)

    # reload batch
    sio.emit('batch_reload', sample_batch_id, namespace='/api')


@sio.event(namespace='/api')
async def match_batch_remove(sid, sample_batch_id):
    # get workspace id
    [workspace_id] = cur.execute("""--sql
        SELECT workspace_id
        FROM sample_batch
        WHERE sample_batch_id == ?
    """, [
        sample_batch_id
    ]).fetchdf().to_dict('records')

    # delete record
    cur.execute("""--sql
        DELETE FROM match
        WHERE sample_item_id IN (
            SELECT sample_item_id
            FROM sample_item
            WHERE sample_batch_id == ?
        )
    """)

    # reload workspace
    sio.emit('workspace_reload', workspace_id, namespace='/api')


# this is not an endpoint
async def match_item_compute(
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

    # Check if file is cached
    cache_item = cache.get(filename, None)
    if not cache_item:
        # File not in cache, load
        print("Loading file: %s" % filename)
        cache_item = load_file(filename, vars=['peaks'])
        cache[filename] = cache_item

    if 'peaks' not in cache_item:
        # Find peaks and write to file
        cache_item = detect_peaks(cache_item)
        cache[filename] = cache_item

    peaks = get_peaks(cache_item)

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
