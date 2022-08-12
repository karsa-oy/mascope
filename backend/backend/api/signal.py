import asyncio
import numpy as np

from backend.lib.peak import mz_calibrate_tof
# from backend.lib.hardware.tofwerk.lib.TwTool import TwTof2Mass
# from backend.lib.hardware.tofwerk.generator import remove_duplicate_mz_values

from backend.lib.file import (
    get_zarr_var_shape,
    load_coord,
    update_props,
    update_zarr_array_coord,
)

from backend.server import sio

# File cache
cache = {}


@sio.event(namespace='/api')
async def calibration_mz_fit(sid, peak_tofs, peak_mzs, exact_mzs):
    mz_calib, stats = mz_calibrate_tof(
        peak_tofs,
        peak_mzs,
        exact_mzs
    )
    return {
        'fit': mz_calib,
        'stats': {
            'postMz': stats['new_mz'].astype(np.float32).tobytes(),
            'postDmz': stats['post_dmz'].astype(np.float32).tobytes(),
            'postDmzNorm': stats['post_dmz_norm'],
            'preDmzNorm': stats['pre_dmz_norm'],
        }
    }


@sio.event(namespace='/api')
async def calibration_mz_apply(sid, fit, filenames):
    global cache

    mode = fit['mode']
    par = fit['par']

    nbr_samples = get_zarr_var_shape(filenames[0], 'signal')[0]

    par = np.array(par, dtype=np.double)
    new_mz = np.array([
        TwTof2Mass(tof, mode, par)
        for tof in range(nbr_samples)
    ])
    new_mz = remove_duplicate_mz_values(new_mz)
    new_range = [new_mz[0], new_mz[-1]]

    for filename in filenames:
        print("Calibrating file: %s" % filename)
        if nbr_samples != get_zarr_var_shape(filename, 'signal')[0]:
            raise Exception("Number of TOF samples does not match")
        # Write new mz coordinates to file
        update_zarr_array_coord(filename, 'signal', 'mz', new_mz)
        peak_tofs = load_coord(filename, 'peaks', 'tof')
        new_peak_mzs = new_mz[peak_tofs.astype(int)]
        update_zarr_array_coord(filename, 'peaks', 'mz', new_peak_mzs)
        update_props(filename, {'range': new_range})
        cache_item = cache.get(filename)
        if cache_item:
            cache_item['mz'] = new_mz
            cache_item.attrs['props'].update({'range': new_range})
            cache[filename] = cache_item

        await sio.emit('dataset_coord_updated', {
            'filename': filename,
            'coord': 'mz',
            'var': 'signal'
        })
        await sio.emit('sample_file_update_request', {
            'id': filename,
            'mz_calibration': fit
        })
        await asyncio.sleep(0)
