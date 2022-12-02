import asyncio
import json
import numpy as np
import pandas as pd

from concurrent.futures import ProcessPoolExecutor

from backend.lib.file import load_file, zarr_sdk
from backend.lib.signal.peak import fit_n_peaks
from backend.server import sio
from backend.db.conn import conn


def read_instrument_functions(filename):
    with conn:
        sample_file_df = pd.read_sql(f"""
            SELECT
                datetime_utc,
                instrument
            FROM
                sample_file
            WHERE
                filename = ?
            """,
            conn,
            params=[filename]
            )
        [instrument] = sample_file_df.instrument
        [file_timestamp] = sample_file_df.datetime_utc
        instrument_function_df = pd.read_sql(f"""
            SELECT
                peakshape,
                resolution_function
            FROM
                instrument_function
            WHERE
                instrument = ?
                AND
                datetime_utc = (
                    SELECT
                         MAX(datetime_utc)
                    FROM
                        instrument_function
                    --WHERE datetime_utc < ?
                    LIMIT 1
                )
            """,
            conn,
            # params=[instrument, file_timestamp]
            params=[instrument]
            )
    peakshape = json.loads(instrument_function_df.peakshape[0])
    p1, p2 = json.loads(instrument_function_df.resolution_function[0])
    R = lambda m: m / (p1 * m + p2)
    return peakshape, R

def get_u_list(sample_batch_id):
    # get sample batch
    with conn:
        [sample_batch] = pd.read_sql(f"""
            SELECT build_params
            FROM sample_batch
            WHERE sample_batch_id == ?
            """,
            conn,
            params=[sample_batch_id]
            ).to_dict('records')
    build_params = json.loads(sample_batch['build_params'])
    calibration_collection_id = build_params['calibration_collection']
    ion_mechanism_ids = build_params['ion_mechanisms']
    with conn:
        target_collection_ids = pd.read_sql(f"""
            SELECT target_collection_id
            FROM target_collection_in_sample_batch
            WHERE sample_batch_id == ?
            """,
            conn,
            params=[sample_batch_id]
            )['target_collection_id'].tolist()
    target_collection_ids.append(calibration_collection_id)
    with conn:
        target_collection_id_refs = ','.join('?'*len(target_collection_ids))
        ion_mechanism_id_refs = ','.join('?'*len(ion_mechanism_ids))
        target_isotope_mzs = pd.read_sql(f"""
            SELECT mz
            FROM target_compound_in_target_collection
            NATURAL JOIN target_compound
            NATURAL JOIN target_ion
            NATURAL JOIN target_isotope
            WHERE target_collection_id IN ({target_collection_id_refs})
            AND ionization_mechanism_id IN ({ion_mechanism_id_refs})
            """,
            conn,
            params=[*target_collection_ids, *ion_mechanism_ids]
            )['mz'].tolist()
    return np.unique(np.round(target_isotope_mzs))



async def detect_peaks(filename, u_list=None):
    dmz = .5
    peakshape, R = read_instrument_functions(filename)
    sample_file_data = load_file(filename, vars=['signal'])
    mz = sample_file_data.mz
    sum_spec = sample_file_data.signal.sum(dim='time').compute()
    if not u_list:
        # Fit all peaks
        u_list = range(10, np.floor(mz[-1])+1)
    executor = ProcessPoolExecutor()
    loop = asyncio.get_event_loop()
    futures = [
        loop.run_in_executor(
            executor,
            fit_n_peaks,
            mz.sel(mz=slice(u-dmz, u+dmz)).compute().values,
            sum_spec.sel(mz=slice(u-dmz, u+dmz)).compute().values,
            peakshape,
            R(u),
            5, # TODO: max n peaks
            .9 # TODO: threshold
        )
        for u in u_list
    ]
    all_peaks = []
    for i, future in enumerate(asyncio.as_completed(futures, loop=loop)):
        fit, peaks = await future
        all_peaks.extend(peaks)
        print("progress: %.2f" %((i+1)/len(futures)))
    executor.shutdown()
    peak_mzs = np.sort(list(zip(*all_peaks))[0])
    print("write peaks to: %s" %filename)
    sample_file_data = sample_file_data.assign_coords(
            tof=('mz', np.arange(len(sample_file_data.mz)).astype(np.float32))
        )
    peak_profiles = sample_file_data.signal.sel(
        mz=peak_mzs,
        method='nearest'
    )
    zarr_sdk.write_peak_dataset(peak_profiles, sample_file_data)


@sio.event(namespace='/')
async def test_long_running_task(sid):
    filename = 'KLTOF1_Data_2022.10.05_09h50m00s' # TODO
    sample_batch_id = 'TpgFxJWJPKrAL0Id' # TODO
    u_list = get_u_list(sample_batch_id) # TODO

    detect_peaks_task = sio.start_background_task(detect_peaks, filename, u_list)
    await detect_peaks_task
    await sio.emit("long_running_task_completed", room=sid)