# -*- coding: utf-8 -*-
"""
Created on Mon Oct 31 16:32:19 2022

@author: Oskari Kausiala
"""

import numpy as np

from backend.lib.file import load_file

#%%
filename = r'C:\Data\instrument\KLTOF2\2021.08.19\KLTOF2_Comissioning-C4Q-xxx-L_2021.08.19-17h59m16s'
filename = r'C:\Data\instrument\unknown\2021.08.19\unknown_Comissioning-C4Q-xxx-L_2021.08.19-17h59m16s'
cache_item = load_file(filename, vars=['signal'])

mz = cache_item.mz
spec = cache_item.signal.sum(dim='time')

#%%
from backend.lib.signal.peak import load_peakshape_mat

peakshape_file = r'C:\Users\Oskari Kausiala\Documents\Repositories\labbis\parameters\peakShapes\peakshape.mat'    
peakshape = load_peakshape_mat(peakshape_file)

p1 = 0.000125
p2 = 0.002545
R = lambda m: m / (p1 * m + p2)

# R = lambda m: R0 - (R0 / (1 + np.exp((m - m0) / dm)))


#%%
from backend.lib.signal.peak import fit_n_peaks

# def calculate_peak_areas(x, y, peakshape, peaks):
#     kernel = np.zeros((len(x), len(peaks)))
#     for i, (pos, hei, res) in enumerate(peaks):
#         peak_kernel = gen_peak(x, pos, hei, res, peakshape)
#         kernel[:, i] = peak_kernel
#         print(sum(peak_kernel))
#     _, _, _, peak_areas = np.linalg.lstsq(kernel, y, rcond=None)
#     peaks = [
#         (pos, hei, res, peak_areas[i])
#         for i, (pos, hei, res) in enumerate(peaks)
#         ]
#     return peaks

um = 125
dmz = .3
umz = mz.sel(mz=slice(um-dmz, um+dmz)).compute().values
uspec = spec.sel(mz=slice(um-dmz, um+dmz)).compute().values

#%%
fit, peaks = fit_n_peaks(
    umz,
    uspec,
    peakshape,
    R,
    max_n_peaks=10,
    threshold=.9
    )

#%
from backend.lib.signal.peak import gen_peak
from matplotlib import pyplot as plt

plt.plot(umz, uspec)
for pos, hei, res, area in peaks:
    plt.plot(umz, gen_peak(umz, pos, hei, res, peakshape))
plt.plot(umz, fit.residual)

print(list(zip(*peaks))[3])

#%%
from backend.lib.signal.peak import fwhm_to_sigma, gen_gaussian_peakshape, gen_peak
from matplotlib import pyplot as plt
from scipy.interpolate import interp1d

min_signal_norm = 5000
good_residual_to_signal_ratio = 0.1
dmz = .3

gaussian_peakshape = gen_gaussian_peakshape()

all_peaks = []
peakshapes = []
ps_x = np.linspace(-30, 30, 601)

for um in range(32, 600):
    print(um)
    fit = None
    peaks = []
    umz = mz.sel(mz=slice(um-dmz, um+dmz)).compute().values
    uspec = spec.sel(mz=slice(um-dmz, um+dmz)).compute().values
    
    uspec_norm = np.linalg.norm(uspec)
    
    if uspec_norm > min_signal_norm:
        fit, peaks = fit_n_peaks(
            umz,
            uspec,
            gaussian_peakshape,
            R,
            max_n_peaks=1,
            threshold=.5,
            fit_pos=False,
            fit_res=True,
            )
        residual_norm = np.linalg.norm(fit.residual)
        good_fit = residual_norm / uspec_norm <= good_residual_to_signal_ratio
        
        all_peaks.extend(peaks)
    if len(peaks) == 1 and good_fit:
        print("good fit")
        # peakshape
        peak = peaks[0]
        fwhm = peak[0] / peak[2]
        if fwhm > 0.1:
            continue
        sigma = fwhm_to_sigma(fwhm)
        uspec_n = uspec / max(uspec)
        mz_n = umz - peak[0]
        ind = np.logical_and(mz_n >= -dmz, mz_n <= +dmz)
        ps_x_u = mz_n[ind] / sigma
        ps_y_u = interp1d(ps_x_u, uspec_n[ind], bounds_error=False, fill_value=0)(ps_x)
        peakshapes.append(ps_y_u)
peakshapes = np.array(peakshapes)
plt.plot(peakshapes.T)
plt.plot(np.median(peakshapes, axis=0))
#%%
    plt.figure()
    plt.plot(umz, uspec)
    for pos, hei, res, area in peaks:
        plt.plot(umz, gen_peak(umz, pos, hei, res, peakshape))
    if fit:
        plt.plot(umz, fit.residual)
        
#%%
max_res = max(list(zip(*all_peaks))[2])
ok_peaks = [peak for peak in all_peaks if peak[2] >= 0.5*max_res]

plt.scatter(list(zip(*ok_peaks))[0], list(zip(*ok_peaks))[2])

#%%
import asyncio
from concurrent.futures import ProcessPoolExecutor
from time import time, sleep

from backend.lib.signal.peak import fit_n_peaks



async def sample_deconvolve(sid, mz, spec, u_list, peakshape, R):
    dmz = .5
    print("init executor")
    t0 = time()
    n_jobs = 4
    executor = ProcessPoolExecutor(max_workers=n_jobs)
    loop = asyncio.get_event_loop()
    print("init futures")
    futures = [
        loop.run_in_executor(
            executor,
            fit_n_peaks,
            mz.sel(mz=slice(u-dmz, u+dmz)).compute().values,
            spec.sel(mz=slice(u-dmz, u+dmz)).compute().values,
            peakshape,
            R(u),
            10,
            .9
        )
        for u in u_list
    ]
    # await sio.emit("long_running_task_started", room=sid)
    t1 = time()
    print("took %.2f s total to initialize; %.2f per process, %.2f per u" %((t1-t0), (t1-t0)/n_jobs, (t1-t0)/len(u_list)))
    print("wait for futures")
    for future in asyncio.as_completed(futures):
        result = await future
        print("task completed")
        # print(result)
    t2 = time()
    print("took %.2f s" %(t2-t1))
    print("took %.2f s total to perform tasks; %.2f per process, %.2f per u" %((t2-t1), (t2-t1)/n_jobs, (t2-t1)/len(u_list)))
    print("shutdown executor")
    executor.shutdown()
    # await sio.emit("long_running_task_completed", room=sid)
    t3 = time()
    print("all done in %.2f s" %(t3-t0))

#%%
import json
import numpy as np
import pandas as pd

from backend.db.conn import conn
from backend.lib.file import load_file
from backend.lib.signal.peak import load_peakshape_mat

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
                    WHERE datetime_utc < ?
                    LIMIT 1
                )
            """,
            conn,
            params=[instrument, file_timestamp]
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
    

async def on_sample_item_process(sid, sample_items):
    # Create sample item records
    sample_item_df = sample_item_create(sample_items)
    [sample_batch_id} = np.unique(sample_item_df['sample_batch_id'].tolist())
    
    # deconvolve
    u_list = get_u_list(sample_batch_id)
    filenames = sample_item_df['filename'].tolist()
    for filename in filenames:
        peakshape, R = read_instrument_functions(filename)
        sample_file = load_file(filename, vars=['signal'])
        mz = sample_file.mz
        sum_spec = sample_file.signal.sum(dim='time').compute()
        sio.start_background_task(
            sample_deconvolve,
            sid,
            mz,
            spec,
            u_list,
            peakshape,
            R
        )
filename = 'KLTOF2_Comissioning-C4Q-xxx-L_2021.08.19-17h59m16s'
sample_batch_id = 'nYfhf5AngZLXisfh'

cache_item = load_file(filename, vars=['signal'])
mz = cache_item.mz
spec = cache_item.signal.sum(dim='time').compute()