import json
import numpy as np
import pandas as pd
import asyncio

from backend.db.conn import conn
from backend.db.id import gen_id
from backend.lib.file import load_file
from backend.lib.peak import (
    detect_peaks,
    get_peaks,
    read_instrument_functions,
)
from backend.lib.chemistry import match_mz
from backend.server import sio


async def compute_matches(
    filename,
    target_collection_ids,
    ionization_mechanism_ids,
    ):
    # Note:
    #   Matching is done on isotope-level. Ion, compound
    #   and collection level matches are aggregated from
    #   isotope-level matches on read; see the frontend
    #   sample store module for this aggregation.

    collection_id_refs = ','.join('?'*len(target_collection_ids))
    mechanism_id_refs = ','.join('?'*len(ionization_mechanism_ids))
    # load target isotopes
    target_isotope_df = pd.read_sql(
        f"""
        SELECT DISTINCT
            target_isotope_id,
            target_ion_id,
            mz,
            relative_abundance
        FROM
            target_collection
            NATURAL JOIN target_compound_in_target_collection
            NATURAL JOIN target_ion
            NATURAL JOIN target_isotope
        WHERE
            target_collection_id IN ({collection_id_refs})
            AND ionization_mechanism_id IN ({mechanism_id_refs})
        """,
        conn,
        params=[*target_collection_ids, *ionization_mechanism_ids]
        )

    #########################
    # STEP 1 - Load or detect peaks #
    #########################

    # Find peaks and write to file
    u_list = list( np.unique(np.round(target_isotope_df.mz)) )
    sample_file = await detect_peaks(filename, u_list, if_exists='append')
    peaks = get_peaks(sample_file, 'area')

    #########################
    # STEP 2 - Prepare data #
    #########################

    # init match df from target isotopes
    match_isotope_df = (
        target_isotope_df.copy()
        .assign(
            match_id=np.nan,
            sample_peak_id=np.nan,
            sample_peak_mz=np.nan,
            sample_peak_area=np.nan,
            sample_peak_area_relative=np.nan,
            match_abundance_error=np.nan,
            match_mz_error=np.nan,
            match_score=np.nan,
        )
    )

    # parse peak data
    peak_mzs = peaks.mz.values
    peak_areas = peaks.sum(dim='time').values
    peak_tofs = peaks.tof.values
    peak_sorting = np.argsort(peak_mzs)

    #############################
    # STEP 3 - Perform matching #
    #############################

    def match(row):
        # Get all peaks within unit mass window
        mz_tolerance = 0.5
        target_mz = row.mz
        match_indeces, match_mzs = match_mz(
            target_mz,
            peak_mzs[peak_sorting],
            tolerance=mz_tolerance
        )
        # Find closest match
        for match_index in match_indeces:
            # get match peak
            peak_index = peak_sorting[match_index]
            peak_mz = peak_mzs[peak_index]
            peak_area = peak_areas[peak_index]
            # check current best match
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
            row['sample_peak_area'] = peak_area
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
        .groupby(['target_ion_id'], as_index=False)['sample_peak_area']
        .sum()
    )
    # join sums back to the isotope level
    isotope_level_peak_sums = pd.merge(
        match_isotope_df,
        ion_level_peak_sums.rename(
            columns={'sample_peak_area': 'sample_peak_area_sum'}
        ),
        on=['target_ion_id'], how='left'
    )

    # compute relative peak heights
    match_isotope_df.loc[:, 'sample_peak_area_relative'] = (
        match_isotope_df['sample_peak_area']
        / isotope_level_peak_sums['sample_peak_area_sum']
    )
    # calculate isotope ratio errors
    match_isotope_df.loc[:, 'match_abundance_error'] = (
        match_isotope_df['relative_abundance']
        * (
            match_isotope_df['sample_peak_area_relative']
            - match_isotope_df['relative_abundance']
        )
    ) * 0 # TODO: match_abundance_error set to 0 for now

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
    return match_isotope_df

async def compute_raw_intensities(
    filename,
    target_collection_ids,
    ionization_mechanism_ids,
    ):
    collection_id_refs = ','.join('?'*len(target_collection_ids))
    mechanism_id_refs = ','.join('?'*len(ionization_mechanism_ids))
    # load target isotopes
    target_isotope_df = pd.read_sql(
        f"""
        SELECT DISTINCT
            target_isotope_id,
            target_ion_id,
            mz,
            relative_abundance
        FROM
            target_collection
            NATURAL JOIN target_compound_in_target_collection
            NATURAL JOIN target_ion
            NATURAL JOIN target_isotope
        WHERE
            target_collection_id IN ({collection_id_refs})
            AND ionization_mechanism_id IN ({mechanism_id_refs})
        """,
        conn,
        params=[*target_collection_ids, *ionization_mechanism_ids]
        )

    sample_file_data = load_file(filename, vars=['signal'])
    sum_spectrum = sample_file_data.signal.sum(dim='time').compute()

    _, R = read_instrument_functions(filename)

    # init interference df from target isotopes
    isotope_interference_df = (
        target_isotope_df.copy()
        .assign(
            sample_peak_interference=np.nan,
        )
    )

    def calc_raw_intensity(row):
        target_mz = row.mz
        dmz = (target_mz / R(target_mz)) / 2 # hwhm
        target_raw_intensity = sum_spectrum.sel(
            mz=slice(target_mz-dmz, target_mz+dmz)
        ).sum(dim='mz')
        row['match_interference_id'] = gen_id(length=32)
        row['sample_peak_interference'] = target_raw_intensity.compute().item()
        return row

    isotope_interference_df = (
        isotope_interference_df
        .apply(calc_raw_intensity, axis=1)
    )

    return isotope_interference_df

@sio.event(namespace='/')
async def match_batch_compute(sid, sample_batch_id):

    # clear previous matches
    await match_batch_remove(sid, sample_batch_id)

    with conn:
        # fetch item ids
        sample_items = pd.read_sql(f"""
            SELECT
                sample_item_id,
                sample_batch_id,
                filename
            FROM sample_item
            WHERE sample_batch_id == ?
            """,
            conn,
            params=[sample_batch_id]
            ).to_dict('records')
    for sample_item in sample_items:
        try:
            await item_compute(sample_item)
        except Exception as e:
            print("Processing sample %s failed: %s" %(sample_item, e))
    # reload batch
    await sio.emit('sample_batch_reload', room=sample_batch_id, namespace='/')

@sio.event(namespace='/')
async def match_batch_remove(sid, sample_batch_id):
    with conn:
        # get workspace id
        workspace_id = pd.read_sql(f"""--sql'
            SELECT workspace_id
            FROM sample_batch
            WHERE sample_batch_id == ?
        """,
        conn,
        params=[sample_batch_id]
        ).to_dict('records')

        # delete record
        conn.cursor().execute(f"""--sql
            DELETE FROM match
            WHERE sample_item_id IN (
                SELECT sample_item_id
                FROM sample_item
                WHERE sample_batch_id == ?
            )
        """,
        [sample_batch_id]
        )
        conn.cursor().execute(f"""--sql
            DELETE FROM match_interference
            WHERE sample_item_id IN (
                SELECT sample_item_id
                FROM sample_item
                WHERE sample_batch_id == ?
            )
        """,
        [sample_batch_id]
        )
    # reload workspace
    await sio.emit('workspace_reload', workspace_id, namespace='/')


async def item_compute(sample_item):
    with conn:
        sample_item_id = sample_item['sample_item_id']
        filename = sample_item['filename']
        sample_batch_id = sample_item['sample_batch_id']
        # get sample batch
        sample_batch = pd.read_sql(
            f"""--sql
            SELECT build_params
            FROM sample_batch
            WHERE sample_batch_id == ?
            """,
            conn,
            params=[sample_batch_id]
            ).to_dict('records')[0]
        # get ionization mechanisms
        ion_mechanisms = json.loads(
            sample_batch['build_params']
            )['ion_mechanisms']
        ion_mechanism_df = pd.DataFrame.from_dict({
            'ionization_mechanism_id': ion_mechanisms
        })
        ionization_mechanism_ids = (
            ion_mechanism_df['ionization_mechanism_id'].tolist()
        )
        target_collection_ids = pd.read_sql(
            f"""--sql
            SELECT target_collection_id
            FROM target_collection_in_sample_batch
            WHERE sample_batch_id == ?
            """,
            conn,
            params=[sample_batch_id]
            )['target_collection_id'].tolist()

    # Compute
    print("Computing interferences for file: %s" % filename)
    match_interference_df = await compute_raw_intensities(
        filename,
        target_collection_ids,  
        ionization_mechanism_ids
        )
    print("Computing matches for file: %s" % filename)
    match_isotope_df = await compute_matches(
        filename,
        target_collection_ids,  
        ionization_mechanism_ids
        )
    with conn:
        # save to database
        # interferences
        match_interference_df = match_interference_df.assign(
            sample_item_id=sample_item_id
        )
        match_interference_df = match_interference_df[[
            "match_interference_id"
            ,"target_isotope_id"
            ,"sample_item_id"
            ,"sample_peak_interference"
        ]]
        match_interference_df.to_sql(
            'match_interference',
            conn,
            if_exists='append',
            index=False
            )
    if len(match_isotope_df) == 0:
        print("No matches found")
        return sample_item
    with conn:
        # save to database
        # matches
        match_isotope_df = match_isotope_df.assign(
            sample_item_id=sample_item_id
        )
        match_isotope_df = match_isotope_df[[
            "match_id"
            ,"target_isotope_id"
            ,"sample_item_id"
            ,"sample_peak_id"
            ,"sample_peak_mz"
            ,"sample_peak_area"
            ,"sample_peak_area_relative"
            ,"sample_peak_tof"
            ,"match_abundance_error"
            ,"match_mz_error"
            ,"match_score"
        ]]
        match_isotope_df.to_sql(
            'match',
            conn,
            if_exists='append',
            index=False
            )
    return sample_item

@sio.event(namespace='/')
async def match_item_compute(sid, sample_item):
    filename = sample_item['filename']
    [instrument] = pd.read_sql(f"""--sql
            SELECT instrument
            FROM sample_file
            WHERE filename = ?
            """,
            conn,
            params=[filename]
        )['instrument'].tolist()
    try:
        await sio.emit(
            'match_item_compute_started',
            {
                'filename': filename,
                'progress': 0,
            },
            room=instrument,
            namespace='/'
        )
        await sio.emit(
            'match_item_compute_progress',
            {},
            room=instrument,
            namespace='/'
        )
        task = sio.start_background_task(
            item_compute, sample_item
        )
        await asyncio.gather(task)
        await sio.emit(
            'match_item_compute_finished',
            {
                'filename': filename,
                'progress': 100,
            },
            room=instrument,
            namespace='/'
        )
        sample_batch_id = sample_item['sample_batch_id']
        await sio.emit(
            'sample_batch_reload',
            room=sample_batch_id,
            namespace='/'
            )
    except:
        await sio.emit(
            'match_item_compute_failed',
            {
                'filename': filename,
                'progress': 100,
            },
            room=instrument,
            namespace='/'
        )

def item_remove(sample_item_id):
    with conn:
        # fetch batch id
        sample_batch_id = pd.read_sql(f"""
            SELECT sample_batch_id
            FROM sample_item
            WHERE sample_item_id == ?
            """,
            conn,
            params=[sample_item_id]
            )['sample_batch_id'].tolist()[0]
        # delete record
        conn.cursor().execute(f"""--sql
            DELETE FROM match
            WHERE sample_item_id == ?
            """,
            [sample_item_id]
            )
        conn.cursor().execute(f"""--sql
            DELETE FROM match_interference
            WHERE sample_item_id == ?
            """,
            [sample_item_id]
            )

@sio.event(namespace='/')
async def match_item_remove(sid, sample_item_id):
    item_remove(sample_item_id)
    # reload batch
    await sio.emit(
        'sample_batch_reload',
        room=sample_batch_id,
        namespace='/'
    )