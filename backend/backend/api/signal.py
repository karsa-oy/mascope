import numpy as np

from zarr.errors import PathNotFoundError

from backend.lib.hardware.tofwerk.lib.TwTool import TwTof2Mass
from backend.lib.file import (
    get_zarr_var_shape,
    load_coord,
    update_props,
    update_zarr_array_coord,
)


def remove_duplicate_mz_values(mz):
    # Sometimes TOF signal mz coordinate contains multiple zeros at the beginning
    # This may cause duplicate coordinate value error in some functions
    # This function fixes the coordinate vector by setting arbitrary small values for
    # the zero coordinates
    mz_unique = mz
    mz_below_10_mask = mz < 10
    if (np.diff(mz[mz_below_10_mask]) == 0).any():
        mz_below_10_maxi = mz_below_10_mask.sum()
        mz_unique[mz_below_10_mask] = np.linspace(
                                            0,
                                            mz[mz_below_10_maxi],
                                            mz_below_10_maxi,
                                            endpoint=False
                                            )
    return mz_unique

async def signal_mz_calibration_update(fit, filenames):
    mode = fit['mode']
    par = fit['par']
    # Calculate new mz axis
    nbr_samples = get_zarr_var_shape(filenames[0], 'signal')[0]
    par = np.array(par, dtype=np.double)
    new_mz = np.array([
        TwTof2Mass(tof, mode, par)
        for tof in range(nbr_samples)
    ])
    new_mz = remove_duplicate_mz_values(new_mz)
    new_range = [new_mz[0], new_mz[-1]]
    # Update zarr file coordinates and props
    for filename in filenames:
        print("Calibrating file: %s" % filename)
        if nbr_samples != get_zarr_var_shape(filename, 'signal')[0]:
            raise Exception("Number of TOF samples does not match")
        update_props(
            filename,
            {
                'range': new_range,
                'mz_calibration': fit    
            }
            )
        # Write new mz coordinates to zarr file
        update_zarr_array_coord(filename, 'signal', 'mz', new_mz)
        try:
            peak_tofs = load_coord(filename, 'peaks', 'tof')
            new_peak_mzs = new_mz[peak_tofs.astype(int)]
            update_zarr_array_coord(filename, 'peaks', 'mz', new_peak_mzs)
        except PathNotFoundError:
            pass
    return new_mz