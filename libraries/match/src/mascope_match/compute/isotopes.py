from typing import Literal
import numpy as np
import pandas as pd

from mascope_file.io import load_array
from mascope_file.name import get_instrument_type, get_sample_file_type
from mascope_signal.compute import get_scan_timestamps
from mascope_signal.peak import detect_peaks
from mascope_chem.mz import match_mz
from mascope_match.runtime import runtime

from mascope_match.params import (
    ORBI_FITTING_THRESHOLD,
    TOF_FITTING_THRESHOLD,
    UnmatchedIsotopeParams,
)
from mascope_match.id import generate_id


async def compute_match_isotopes(
    filename: str,
    target_isotopes_df: pd.DataFrame,
    min_isotope_abundance: float,
    instrument_functions: tuple[dict, callable],
    polarity: Literal["+", "-"] | None = None,
) -> pd.DataFrame:
    """
    Compute matches between target isotopes and sample file peaks.

    This function identifies the best matching peaks within the sample spectrum for each target isotope
    based on their m/z values and computes match statistics. For isotopes without matching peaks,
    default values are assigned with a match score of 0.

    Steps:
    1. Initialize parameters and load data from the sample file.
    2. Detect peaks in the sample file for potential matches.
    3. Create initial dataframe with placeholders for all target isotopes.
    4. Perform matching between target isotopes and sample peaks.
    5. Calculate match statistics for isotopes with actual matches.
    6. Assign default values for isotopes without matching peaks.
    7. Return a DataFrame containing match details for all target isotopes.

    :param filename: Path to the sample file to be analyzed for matches.
    :type filename: str
    :param target_isotopes_df: DataFrame containing target isotopes with their m/z values and other properties.
    :type target_isotopes_df: pd.DataFrame
    :param min_isotope_abundance: Minimum relative abundance threshold for isotopes to be considered in matching.
    :type min_isotope_abundance: float
    :param instrument_functions: Tuple containing peak shape details and a resolution function R.
    :type instrument_functions: tuple[dict, callable]
    :param polarity: Polarity of the sample, either "+", "-", or "+-".
    :type polarity: Literal["+", "-"], optional
    :return: DataFrame with match details for all target isotopes, including those without matches
    :rtype: pd.DataFrame
    :raises ValueError: If an error occurs during the matching process.

    Notes:
    - Matching is done at the isotope level. Ion, compound and collection level matches are
      aggregated in a separate process.
    - Isotopes without matching peaks are assigned a match score of 0 and placeholder values
      for the required database fields.

    TODO min_isotope_abundance will be passed from the match_params
    """
    try:
        # Step 1: Initialize parameters and load data
        instrument_type = get_instrument_type(filename)
        resolution_type = "LOW" if instrument_type == "tof" else "HIGH"
        unmatched_defaults = UnmatchedIsotopeParams()

        # Filter isotopes below threshold and with incorrect resolution
        query = "relative_abundance >= @min_isotope_abundance and resolution == @resolution_type"
        target_isotopes_df = target_isotopes_df.query(query).reset_index(drop=True)

        # Step 2: - Detect peaks in the sample file

        # Find peaks and write to file
        u_list = list(np.unique(np.round(target_isotopes_df.mz)))

        # Assign peak fitting threshold depending on the instrument type
        # Correct intrument type unsured by get_instrument_type
        if instrument_type == "orbi":
            threshold = ORBI_FITTING_THRESHOLD
        if instrument_type == "tof":
            threshold = TOF_FITTING_THRESHOLD

        # Detect peaks in the sample file
        await detect_peaks(
            filename,
            instrument_functions,
            threshold,
            u_list,
            if_exists="append",
            instrument_type=instrument_type,
        )

        runtime.logger.debug("Start matching")

        # Load the appropriate peak data based on instrument type
        if instrument_type == "orbi":
            peaks = load_array(filename, "peak_heights").peak_heights
        if instrument_type == "tof":
            peaks = load_array(filename, "peak_areas").peak_areas

        sample_file_type = get_sample_file_type(filename)
        if sample_file_type in ["orbi_zarr", "tof_zarr"]:
            peaks = peaks.dropna(dim="mz", how="all")

        if polarity:
            # Filter peaks based on polarity
            time_scan = get_scan_timestamps(filename, polarity=polarity)
            peaks = peaks.sel(time=time_scan, method="nearest")

        # Step 3: Create initial dataframe with default values for all isotopes
        match_isotope_df = target_isotopes_df.copy().assign(
            match_isotope_id=[
                generate_id(length=32) for _ in range(len(target_isotopes_df))
            ],
            sample_peak_id=np.nan,
            sample_peak_mz=np.nan,
            sample_peak_intensity=np.nan,
            sample_peak_intensity_relative=np.nan,
            match_abundance_error=np.nan,
            match_isotope_correlation=np.nan,
            match_mz_error=np.nan,
            match_score=unmatched_defaults.match_score,
            sample_peak_tof=np.nan,
        )

        # Step 4: Extract peak data for matching
        runtime.logger.debug("Parse peak data")
        peak_intensities = peaks.mean(dim="time").compute().values
        # Filter for non-zero intensities
        non_zero_peaks = peak_intensities > 0
        peak_intensities = peak_intensities[non_zero_peaks]
        peak_mzs = peaks.mz.values[non_zero_peaks]
        peak_tofs = peaks.tof.values[non_zero_peaks]
        peak_sorting = np.argsort(peak_mzs)

        # Step 5: Perform matching
        def match(row):
            # Get all peaks within unit mass window
            mz_tolerance = 0.5
            target_mz = row.mz
            match_indices, _ = match_mz(
                target_mz, peak_mzs[peak_sorting], tolerance=mz_tolerance
            )

            # Find closest match
            for match_index in match_indices:
                # Get match peak
                peak_index = peak_sorting[match_index]
                peak_mz = peak_mzs[peak_index]
                peak_intensity = peak_intensities[peak_index]

                # Check if better than current match
                best_match = row.sample_peak_id
                if not np.isnan(best_match):
                    prev_mz_err = abs(row.sample_peak_mz - target_mz)
                    new_mz_err = abs(peak_mz - target_mz)
                    if new_mz_err > prev_mz_err:
                        continue

                # Save match
                row["sample_peak_id"] = peak_index
                row["sample_peak_mz"] = peak_mz
                row["sample_peak_tof"] = peak_tofs[int(peak_index)]
                row["sample_peak_intensity"] = peak_intensity
            return row

        # Apply matching to all isotopes
        match_isotope_df = match_isotope_df.apply(match, axis=1).reset_index()

        # Create a mask for matched isotopes (those with actual peak data)
        matched_mask = ~match_isotope_df["sample_peak_mz"].isna()

        # Step 6: - Calculate match stats for isotopes with actual matches
        if matched_mask.any():
            # Calculate ion-level statistics - isotope ratios, sum matched sample peak intensities for each ion
            ion_level_peak_sums = match_isotope_df.groupby(
                "target_ion_id", as_index=False
            )["sample_peak_intensity"].sum()

            # Join sums back to the isotope level
            isotope_level_peak_sums = pd.merge(
                match_isotope_df,
                ion_level_peak_sums.rename(
                    columns={"sample_peak_intensity": "sample_peak_intensity_sum"}
                ),
                on="target_ion_id",
                how="left",
            )

            # Calculate relative peak intensities
            match_isotope_df.loc[:, "sample_peak_intensity_relative"] = (
                match_isotope_df["sample_peak_intensity"]
                / isotope_level_peak_sums["sample_peak_intensity_sum"]
            )

            # Calculate abundance matching errors
            match_isotope_df.loc[:, "match_abundance_error"] = match_isotope_df[
                "relative_abundance"
            ] * (
                match_isotope_df["sample_peak_intensity_relative"]
                - match_isotope_df["relative_abundance"]
            )

            # Calculate isotope correlations by ion group
            match_isotope_df = match_isotope_df.groupby(
                ["target_ion_id"], group_keys=False
            ).apply(
                lambda ion_group: (
                    ion_group.assign(
                        match_isotope_correlation=(
                            np.corrcoef(
                                np.array(
                                    [
                                        peaks.sel(mz=peak_mz, method="nearest")
                                        for peak_mz in ion_group["sample_peak_mz"]
                                    ]
                                )
                            )[0, 1]
                            if len(ion_group) > 1
                            else 1
                        )
                    )
                )
            )
            match_isotope_df["match_isotope_correlation"] = match_isotope_df[
                "match_isotope_correlation"
            ].fillna(0.0)

            # Calculate m/z errors (in ppm)
            match_isotope_df.loc[:, "match_mz_error"] = (
                1e6
                * (match_isotope_df["sample_peak_mz"] - match_isotope_df["mz"])
                / match_isotope_df["mz"]
            )

            # Calculate match scores
            def score(row):
                row["match_score"] = (1 - abs(row.match_abundance_error)) * max(
                    0, (1 - 1e-2 * abs(row.match_mz_error))
                )
                return row

            match_isotope_df = match_isotope_df.apply(
                score, axis=1, result_type="broadcast"
            )

        # Step 7: Set default values for unmatched isotopes
        unmatched_mask = ~matched_mask
        if unmatched_mask.any():
            unmatched_count = unmatched_mask.sum()
            runtime.logger.info(
                f"Found {unmatched_count} isotopes without matching peaks"
            )

            # Set sample_peak_mz for unmatched isotopes using target m/z values
            match_isotope_df.loc[unmatched_mask, "sample_peak_mz"] = (
                match_isotope_df.loc[unmatched_mask, "mz"]
            )

            # Apply all defaults except sample_peak_mz which was handled above
            for column, value in unmatched_defaults.model_dump().items():
                if column != "sample_peak_mz":
                    match_isotope_df.loc[unmatched_mask, column] = value

        return match_isotope_df
    except Exception as e:
        error_message = f"Computing matches failed: {e}"
        runtime.logger.error(error_message)
        raise ValueError(error_message) from e
