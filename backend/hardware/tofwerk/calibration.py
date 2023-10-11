import numpy as np

from .lib.TwTool import TwMassCalibrate, TwTof2Mass


def mz_calibrate(peak_tof, peak_mz, exact_mz):
    # Prepare arguments
    mass_calib_mode = 0
    nbr_points = len(peak_tof)
    mass = np.array(exact_mz, dtype=np.double)
    tofs = np.array(peak_tof, dtype=np.double)
    peak_mz = np.array(peak_mz)
    weight = np.ones((nbr_points,))  # TODO: Set weights?
    nbr_params = np.array([2], dtype=np.int32)
    mass_calib_par = np.zeros((nbr_params[0],), dtype=np.double)
    legacy_a = legacy_b = np.array([None], dtype=np.double)
    # Calibrate
    ret = TwMassCalibrate(
        mass_calib_mode,
        nbr_points,
        mass,
        tofs,
        weight,
        nbr_params,
        mass_calib_par,
        legacy_a,
        legacy_b,
    )

    if ret != 4:
        raise Exception("TwMassCalibrate failed with code: %s" % ret)

    mass_calib = {"mode": mass_calib_mode, "par": list(mass_calib_par)}

    new_peak_mz = np.array(
        [TwTof2Mass(tof, mass_calib_mode, mass_calib_par) for tof in tofs]
    )
    pre_dmz = (peak_mz - mass) / mass * 1e6
    post_dmz = (new_peak_mz - mass) / mass * 1e6

    stats = {
        "mz": mass,
        "new_mz": new_peak_mz,
        "pre_dmz": pre_dmz,
        "post_dmz": post_dmz,
    }

    return mass_calib, stats
