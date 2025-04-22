"""
Functionalities related to the m/z fitting calibration processes.
"""

import numpy as np
import pandas as pd
from scipy.optimize import fsolve
from zarr.errors import PathNotFoundError

from mascope_tofwerk.calibration import mz_calibrate

from mascope_file.io import load_coord, update_props, update_zarr_array_coord
from mascope_file.name import get_sample_file_type

from mascope_signal.compute import get_sum_signal, get_tic_per_scan

from mascope_match import compute_match_isotopes
from mascope_backend.api.lib.api_features import (
    api_controller,
)
from mascope_backend.api.new.instrument_configs.lib import (
    read_instrument_functions,
)
from mascope_backend.api.controllers.target.isotopes.target_isotopes_controller import (
    get_target_isotopes,
)
from mascope_backend.api.controllers.target.associations.target_compound_in_target_collection_controller import (
    get_target_compound_in_target_collection,
)
from mascope_backend.socket.notifications import (
    UserNotification,
    send_progress_user_notification,
)
from mascope_backend.api.new.match.params import MZ_ERROR_TOLERANCE, TIC_THRESHOLD

from mascope_backend.runtime import runtime


@api_controller()
async def mz_fit(
    filename,
    calibration_collection_id,
    ionization_mechanism_ids,
    peak_intensity_min,
    isotope_abundance_min,
    match_score_min,
    refine_window,
    notification: UserNotification,
    mz_error_tolerance: int = MZ_ERROR_TOLERANCE,
    tic_threshold: float = TIC_THRESHOLD,
):
    """
    Main function to fit m/z. Fits the mass-to-charge ratio (m/z) for a given sample file.

    :param ...:  parameters.
    :return: fit, stats, error, warning.
    """
    fit = None
    stats = None
    error = None
    warning = None

    await send_progress_user_notification(notification, 0.25)

    # Get TIC
    _, tic_per_scan = get_tic_per_scan(filename)
    tic = np.sum(tic_per_scan)

    if tic < tic_threshold:
        warning = "TIC is too low! Check ionization device."
        return fit, stats, error, warning

    await send_progress_user_notification(notification, 0.35)

    # Compute matches for calibration compounds
    target_compounds_result = await get_target_compound_in_target_collection(
        target_collection_id=calibration_collection_id,
    )
    target_compound_ids = [
        item["target_compound_id"] for item in target_compounds_result["data"]
    ]

    # Fetch target isotopes for specific filters
    target_isotopes_result = await get_target_isotopes(
        target_compound_ids=target_compound_ids,
        ionization_mechanism_ids=ionization_mechanism_ids,
    )
    target_isotopes_df = pd.DataFrame(target_isotopes_result["data"])

    # Get instrument functions for filename
    instrument_functions = await read_instrument_functions(filename)

    match_isotope_df = await compute_match_isotopes(
        filename=filename,
        target_isotopes_df=target_isotopes_df,
        min_isotope_abundance=isotope_abundance_min,
        instrument_functions=instrument_functions,
    )

    # Filter matches
    good_matches_df = match_isotope_df[
        (match_isotope_df.relative_abundance >= isotope_abundance_min)
        & (match_isotope_df.sample_peak_intensity >= peak_intensity_min)
        & (abs(match_isotope_df.match_mz_error) <= refine_window)
        & (match_isotope_df.match_score >= match_score_min)
    ]
    n_relevant_isotopes = len(
        match_isotope_df[(match_isotope_df.relative_abundance >= isotope_abundance_min)]
    )
    calibrant_signal_intensity = good_matches_df["sample_peak_intensity"]
    calibrant_to_tic = calibrant_signal_intensity / tic
    await send_progress_user_notification(notification, 0.75)

    if (
        n_relevant_isotopes > 3
        and len(good_matches_df) > 3
        and (n_relevant_isotopes - len(good_matches_df) <= 2)
    ):
        # Fit mz calibration
        fit, stats = mz_calibrate(
            good_matches_df["sample_peak_tof"],
            good_matches_df["sample_peak_mz"],
            good_matches_df["mz"],
        )
        calibration_df = good_matches_df.copy().assign(
            calibration_mz=stats["new_mz"],
            calibration_mz_error=stats["post_dmz"],
            mz_error_diff=abs(stats["post_dmz"]) - abs(stats["pre_dmz"]),
            calibrant_to_tic=calibrant_to_tic,
        )
        calibration_inaccurate = (
            abs(calibration_df["calibration_mz_error"]) > mz_error_tolerance
        ).any()
        if calibration_inaccurate:
            warning = "Calibration inaccurate"
        stats = calibration_df.to_dict("records")
        summary_row = {
            "match_mz_error": abs(calibration_df["match_mz_error"]).mean(),
            "calibration_mz_error": abs(calibration_df["calibration_mz_error"]).mean(),
            "mz_error_diff": sum(calibration_df["mz_error_diff"]),
            "calibrant_to_tic": sum(calibration_df["calibrant_to_tic"]),
        }
        stats.append(summary_row)

        await send_progress_user_notification(notification, 0.95)
    else:
        # Not enough calibration peaks
        fit = None
        stats = good_matches_df.to_dict("records")
        warning = "Not enough calibration peaks"

    return fit, stats, error, warning


def signal_mz_calibration_update(fit, filename):
    mode = fit["mode"]
    par = fit["par"]
    # Calculate new mz axis
    nbr_samples = get_sum_signal(filename).size
    tof = np.arange(nbr_samples)
    new_mz = tof_to_mass(tof, mode, par)
    new_range = new_mz[0], new_mz[-1]

    # Update zarr file coordinates and props
    runtime.logger.info(f"Calibrating file: {filename}")
    sample_file_type = get_sample_file_type(filename)
    update_props(filename, {"range": new_range, "mz_calibration": fit})
    if sample_file_type != "tof_h5":
        # Write new mz coordinates to zarr file
        update_zarr_array_coord(filename, "signal", "mz", new_mz)
    try:
        update_zarr_array_coord(filename, "sum_signal", "mz", new_mz)
    except PathNotFoundError:
        pass
    try:
        peak_tofs = load_coord(filename, "peak_areas", "tof")
        new_peak_mzs = new_mz[peak_tofs.astype(int)]
        update_zarr_array_coord(filename, "peak_areas", "mz", new_peak_mzs)
        update_zarr_array_coord(filename, "peak_heights", "mz", new_peak_mzs)
    except PathNotFoundError:
        pass
    return new_mz


def tof_to_mass(tof: np.ndarray, mode: int, par: list) -> float | np.ndarray:
    """Convert between sample indices and mass.

    :param tof: Values to convert
    :type tof: np.ndarray
    :param mode: Mass calibration function to use
    :type mode: int
    :param par: List containing the calibration parameters (number depends on mode)
    :type par: list
    """

    def solve_numerically(objective, tof_val):
        m_initial_guess = 1.0
        (m_solution,) = fsolve(objective, m_initial_guess, args=(tof_val,))
        return m_solution

    match mode:
        case 0:
            # from i(m) = p1 * np.sqrt(m) + p2
            return ((tof - par[1]) / par[0]) ** 2
        case 1:
            # from i(m) = p1/np.sqrt(m) + p2
            return (par[0] / (tof - par[1])) ** 2
        case 2:
            # from i(m) = p1 * np.power(m, p3) + p2
            return ((tof - par[1]) / par[0]) ** (1 / par[2])
        case 3:
            objective = (
                lambda m, tof_val: par[0] * np.sqrt(m)
                + par[1]
                + par[2] * (m - par[3]) ** 2
                - tof_val
            )
            return np.vectorize(lambda tof_val: solve_numerically(objective, tof_val))(
                tof
            )
        case 4:
            objective = (
                lambda m, tof_val: par[0] * np.sqrt(m)
                + par[1]
                + par[2] * m**2
                + par[3] * m
                + par[4]
                - tof_val
            )
            return np.vectorize(lambda tof_val: solve_numerically(objective, tof_val))(
                tof
            )
        case 5:
            return par[0] * tof**2 + par[1] * tof + par[2]
        case _:
            raise ValueError(f"Unknown mass calibration mode: {mode}")
