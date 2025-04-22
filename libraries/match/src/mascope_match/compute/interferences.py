import numpy as np
import pandas as pd

from mascope_file.io import load_file
from mascope_file.name import get_instrument_type
from mascope_signal.compute import get_sum_signal
from mascope_signal.peak import calculate_signal_area

from mascope_match.id import generate_id


async def compute_match_interferences(
    filename: str,
    target_isotopes_df: pd.DataFrame,
    instrument_functions: tuple[dict, callable],
) -> pd.DataFrame:
    """
    Computes match interferences for a given sample file based on specified target isotopes.

    This function calculates the raw intensities for each target isotope within the specified mass-to-charge (m/z) range,
    which are used to identify potential interferences in the sample's spectrum. It involves loading the sample file data,
    summing up the spectrum, and then computing the raw intensities for the target isotopes.

    Steps:
    1. Load the sample file and compute the summed spectrum across all time points.
    2. For each target isotope, calculate the raw intensity within a defined m/z range around the target m/z value.

    :param filename: Path to the sample file from which to compute interferences.
    :type filename: str
    :param target_isotopes_df: DataFrame containing the target isotopes and their m/z values.
    :type target_isotopes_df: pd.DataFrame
    :param instrument_functions: Tuple containing peak shape details and a resolution function R.
    :type instrument_functions: tuple[dict, callable]
    :return: DataFrame with computed interferences for each target isotope.
    :rtype: pd.DataFrame
    :raises ValueError: If an error occurs during the computation process.
    """
    try:
        # Step 1: Load the sample file and compute the summed spectrum
        sum_spectrum = get_sum_signal(filename)
        instrument_type = get_instrument_type(filename)

        # Extract resolution function from the provided instrument_functions
        _, R = instrument_functions

        # Step 2: Initialize DataFrame for interferences and compute raw intensities for each target mz
        isotope_interference_df = target_isotopes_df.copy().assign(
            sample_peak_interference=np.nan,
        )

        # Read sample interval if dealing with TOF, default 0.25 for backwards compatibility
        sample_interval = (
            (load_file(filename, vars=[]).attrs["props"].get("sample_interval", 0.25))
            if instrument_type == "tof"
            else None
        )

        def calc_raw_intensity(row):
            target_mz = row.mz
            dmz = (target_mz / R(target_mz)) / 2  # hwhm
            if instrument_type == "tof":
                # For the TOF, calculate signal area in the mz range
                target_raw_intensity = calculate_signal_area(
                    filename,
                    mz_min=target_mz - dmz,
                    mz_max=target_mz + dmz,
                    sum_spectrum=sum_spectrum,
                    sample_interval=sample_interval,
                )
            else:
                # For the Orbitrap, calculate signal maximum intensity in the mz range
                sum_spectrum_slice = sum_spectrum.sel(
                    mz=slice(target_mz - dmz, target_mz + dmz)
                )
                if sum_spectrum_slice.shape[0] == 0:
                    target_raw_intensity = 0
                else:
                    target_raw_intensity = (
                        sum_spectrum_slice.max(dim="mz").compute().item()
                    )
            row["match_interference_id"] = generate_id(length=32)
            row["sample_peak_interference"] = target_raw_intensity
            return row

        isotope_interference_df = isotope_interference_df.apply(
            calc_raw_intensity, axis=1
        )

        return isotope_interference_df
    except Exception as e:
        error_message = f"Computing match interferences failed: {e}"
        raise ValueError(error_message)
