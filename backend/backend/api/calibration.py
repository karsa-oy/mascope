import asyncio
import json
import pandas as pd

from backend.api.match import compute_matches, match_item_remove
from backend.api.match import item_remove as match_item_remove
from backend.api.sample import sample_batch_update
from backend.api.sample import file_update as sample_file_update
from backend.api.signal import signal_mz_calibration_update
from backend.db.conn import conn
from hardware.tofwerk.calibration import mz_calibrate
from backend.server import sio


@sio.event(namespace='/')
async def calibration_mz_calibrate_batch(
    sid,
    sample_batch_id,
    filename
    ):
    with conn:
        # Read sample batch
        sample_batch_df = pd.read_sql("""
            SELECT
                *
            FROM sample_batch
            WHERE sample_batch_id == ?
            """,
            conn,
            params=[sample_batch_id]
        )
        target_collection_ids = pd.read_sql(f"""--sql
            SELECT target_collection_id
            FROM target_collection_in_sample_batch
            WHERE sample_batch_id == ?
            """,
            conn,
            params=[sample_batch_id]
            )['target_collection_id'].tolist()
    sample_batch_df = sample_batch_df.assign(
        target_collection_id=[target_collection_ids]
        )
    sample_batch_df = sample_batch_df.assign(
        build_params=sample_batch_df[['build_params']].applymap(
            lambda x: json.loads(x)
            ),
        filter_params=sample_batch_df[['filter_params']].applymap(
            lambda x: json.loads(x)
            ),
        )
    build_params = sample_batch_df['build_params'].tolist()[0]
    calibration_collection_id = build_params['calibration_collection']
    ionization_mechanism_ids = build_params['ion_mechanisms']
    
    # Compute matches for calibration compounds
    match_isotope_df = compute_matches(
        filename,
        [calibration_collection_id],
        ionization_mechanism_ids
        )
    
    # Fit mz calibration
    fit, stats = mz_calibrate(
        match_isotope_df['sample_peak_tof'],
        match_isotope_df['sample_peak_mz'],
        match_isotope_df['mz']
    )

    # TODO: Check calibration is ok

    # Apply to file
    await calibration_mz_apply(sid, fit, [filename])

    # Update sample batch
    sample_batch_df['calibration_sample_filename'] = filename
    await sample_batch_update(sid, sample_batch_df.to_dict('records'))

async def mz_calibrate_sample(sid, sample_item):
    # get sample batch
    with conn:
        [sample_batch] = pd.read_sql(f"""
            SELECT build_params
            FROM sample_batch
            WHERE sample_batch_id == ?
            """,
            conn,
            params=[sample_item['sample_batch_id']]
            ).to_dict('records')
    # get mz calibration parameters
    build_params = json.loads(sample_batch['build_params'])
    calibration_collection_id = build_params['calibration_collection']
    ion_mechanism_ids = build_params['ion_mechanisms']
    fit, stats = await calibration_mz_fit(
        sid,
        sample_item['filename'],
        [calibration_collection_id],
        ion_mechanism_ids,
        isotope_abundance_min=0.1,
        match_score_min=0,
        refine_window=500
        )
    if not fit:
        raise Exception("Failed to fit m/z calibration")
    await calibration_mz_apply(sid, fit, [sample_item['filename']])

@sio.event(namespace='/')
async def calibration_mz_calibrate_sample(sid, sample_item):
    try:
        filename = sample_item['filename']
    except KeyError:
        print("calibration_mz_calibrate_sample: Invalid sample item %s" %sample_item)
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
            'calibration_mz_calibrate_started',
            {
                'filename': filename,
                'progress': 0,
            },
            room=instrument,
            namespace='/'
        )
        await sio.emit(
            'calibration_mz_calibrate_progress',
            {},
            room=instrument,
            namespace='/'
        )
        task = sio.start_background_task(
            mz_calibrate_sample, sid, sample_item
        )
        await asyncio.gather(task)
        await sio.emit(
            'calibration_mz_calibrate_finished',
            {
                'filename': filename,
                'progress': 100,
            },
            room=instrument,
            namespace='/'
        )
    except Exception as e:
        print("Failed to calibrate sample %s: %s" %(filename, e))
        await sio.emit(
            'calibration_mz_calibrate_failed',
            {
                'filename': filename,
                'progress': 100,
            },
            room=instrument,
            namespace='/'
        )


async def mz_fit(
    filename,
    calibration_collection_ids,
    ionization_mechanism_ids,
    isotope_abundance_min,
    match_score_min,
    refine_window
    ):
    # Compute matches for calibration compounds
    match_isotope_df = await compute_matches(
        filename,
        calibration_collection_ids,
        ionization_mechanism_ids
    )
    # Filter matches
    good_matches_df = match_isotope_df[
        (match_isotope_df.relative_abundance >= isotope_abundance_min)
        & (abs(match_isotope_df.match_mz_error) <= refine_window)
        & (match_isotope_df.match_score >= match_score_min)
        ]

    if len(good_matches_df) > 3:
        # Fit mz calibration
        fit, stats = mz_calibrate(
            good_matches_df['sample_peak_tof'],
            good_matches_df['sample_peak_mz'],
            good_matches_df['mz']
        )
        # TODO: Check calibration is ok
        calibration_df = good_matches_df.copy().assign(
            calibration_mz=stats['new_mz'],
            calibration_mz_error=stats['post_dmz']
            )
        stats = calibration_df.to_dict('records')
    else:
        # Not enough calibration peaks
        fit = None
        stats = None
    return fit, stats

@sio.event(namespace='/')
async def calibration_mz_fit(
    sid,
    filename,
    calibration_collection_ids,
    ionization_mechanism_ids,
    isotope_abundance_min,
    match_score_min,
    refine_window
    ):
    fit, stats = await mz_fit(
        filename,
        calibration_collection_ids,
        ionization_mechanism_ids,
        isotope_abundance_min,
        match_score_min,
        refine_window
        )
    if sid:
        await sio.emit(
            'calibration_mz_fit_stats',
            {
                'fit': fit,
                'stats': stats
            },
            room=sid
        )
    return fit, stats

def mz_apply(fit, sample_filenames):
    # Read sample file records
    sample_filename_refs = ','.join('?'*len(sample_filenames))
    with conn:
        sample_file_df = pd.read_sql(f"""--sql
            SELECT *
            FROM sample_file
            WHERE filename IN (
                {sample_filename_refs}
            )
            """,
            conn,
            params=sample_filenames
            )
    sample_file_df = sample_file_df.assign(
        mz_calibration=sample_file_df[['mz_calibration']].applymap(
            lambda x: json.loads(x) if x is not None else x
            ),
        range=sample_file_df[['range']].applymap(
            lambda x: json.loads(x)
            ),
        )
    # Update zarr files
    filenames = sample_file_df['filename'].tolist()
    new_mz = signal_mz_calibration_update(fit, filenames)
    new_range = [new_mz[0], new_mz[-1]]

    fit.update({'verified': True})
    for _, sample_file in sample_file_df.iterrows():
        # Update database record
        sample_file['mz_calibration'] = fit
        sample_file['range'] = new_range
        sample_file_update(
            [sample_file.to_dict()]
            )
        # Read affected sample items
        with conn:
            sample_item_ids = pd.read_sql(f"""--sql
                SELECT sample_item_id
                FROM sample_item
                NATURAL LEFT JOIN sample_file
                WHERE sample_file_id == ?
                """,
                conn,
                params=[sample_file['sample_file_id']]
                )['sample_item_id'].tolist()
        for sample_item_id in sample_item_ids:
            # Delete outdated matches
            match_item_remove(sample_item_id)
    return sample_item_ids

@sio.event(namespace='/')
async def calibration_mz_apply(sid, fit, sample_filenames):
    sample_item_ids = mz_apply(fit, sample_filenames)
    for sample_item_id in sample_item_ids:
        await sio.emit(
            'calibration_mz_applied',
            sample_item_id,
            room=sample_item_id,
            namespace='/'
            )