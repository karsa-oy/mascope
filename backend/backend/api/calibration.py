import json
import numpy as np
import pandas as pd

from backend.api.match import compute_matches, match_item_compute, match_item_remove
from backend.api.sample import sample_batch_update, sample_file_update
from backend.api.signal import signal_mz_calibration_update
from backend.db.conn import conn
from backend.lib.file import load_file
from backend.lib.hardware.tofwerk.calibration import mz_calibrate
from backend.lib.peak import get_peaks
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

@sio.event(namespace='/')
async def calibration_mz_fit(
    sid,
    filename,
    calibration_collection_ids,
    ionization_mechanism_ids,
    match_score_min,
    refine_window
    ):
    # Compute matches for calibration compounds
    match_isotope_df = compute_matches(
        filename,
        calibration_collection_ids,
        ionization_mechanism_ids
        )

    # Filter matches
    good_matches_df = match_isotope_df[
        (abs(match_isotope_df.match_mz_error) <= refine_window)
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

    await sio.emit(
        'calibration_mz_fit_stats',
        {
            'fit': fit,
            'stats': stats
        },
        room=sid
    )


@sio.event(namespace='/')
async def calibration_mz_apply(sid, fit, sample_filenames):
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
        sample_file_attributes=sample_file_df[['sample_file_attributes']].applymap(
            lambda x: json.loads(x)
            ),
        mz_calibration=sample_file_df[['mz_calibration']].applymap(
            lambda x: json.loads(x) if x is not None else x
            ),
        range=sample_file_df[['range']].applymap(
            lambda x: json.loads(x)
            ),
        )
    # Update zarr files
    filenames = sample_file_df['filename'].tolist()
    new_mz = await signal_mz_calibration_update(fit, filenames)
    new_range = [new_mz[0], new_mz[-1]]

    fit.update({'verified': True})
    for _, sample_file in sample_file_df.iterrows():
        # Update database record
        sample_file['mz_calibration'] = fit
        sample_file['range'] = new_range
        await sample_file_update(
            sid,
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
            await match_item_remove(sid, sample_item_id)
            await sio.emit(
                'calibration_mz_applied',
                sample_item_id,
                room=sample_item_id,
                namespace='/'
                )