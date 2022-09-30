import json
import numpy as np
import pandas as pd

from backend.api.match import compute_matches, match_item_compute, match_item_remove
from backend.api.sample import sample_batch_update, sample_file_update
from backend.api.signal import signal_mz_calibration_update
from backend.db.conn import conn
from backend.lib.file import load_file
from backend.lib.peak import get_peaks, mz_calibrate_tof
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
    fit, stats = mz_calibrate_tof(
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
async def calibration_mz_fit(sid, peak_tofs, peak_mzs, exact_mzs):
    mz_calib, stats = mz_calibrate_tof(
        peak_tofs,
        peak_mzs,
        exact_mzs
    )
    await sio.emit('calibration_mz_fit_stats',
        {
        'fit': mz_calib,
        'stats': {
            'post_mz': stats['new_mz'].astype(np.float32).tobytes(),
            'post_dmz': stats['post_dmz'].astype(np.float32).tobytes(),
            'post_dmz_norm': stats['post_dmz_norm'],
            'pre_dmz_norm': stats['pre_dmz_norm'],
            }
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

    for _, sample_file in sample_file_df.iterrows():
        # Update database record
        sample_file['mz_calibration'] = fit
        sample_file['range'] = new_range
        await sample_file_update(
            sid,
            [sample_file.to_dict()]
            )
        # Read sample items
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
        # Update matches
        # for sample_item_id in sample_item_ids:
        #     await match_item_remove(sid, sample_item_id)
        #     await match_item_compute(sid, sample_item_id)