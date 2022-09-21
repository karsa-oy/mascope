import json
import numpy as np
import pandas as pd

from backend.api.match import match_item_compute, match_item_remove
from backend.api.sample import sample_file_update
from backend.api.signal import signal_mz_calibration_update
from backend.db.conn import conn
from backend.lib.peak import mz_calibrate_tof
from backend.server import sio


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
async def calibration_mz_apply(sid, fit, sample_file_ids):
    # Read sample file records
    sample_file_id_refs = ','.join('?'*len(sample_file_ids))
    with conn:
        sample_file_df = pd.read_sql(f"""--sql
            SELECT *
            FROM sample_file
            WHERE sample_file_id IN (
                {sample_file_id_refs}
            )
            """,
            conn,
            params=sample_file_ids
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
        for sample_item_id in sample_item_ids:
            await match_item_remove(sid, sample_item_id)
            await match_item_compute(sid, sample_item_id)