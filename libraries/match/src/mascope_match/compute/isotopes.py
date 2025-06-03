from typing import Literal
import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist

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
    match_params: "MatchParams",  # noqa: F821 # type: ignore
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
    :param match_params: Match parameters containing settings for the matching process.
    :type match_params: BaseMatchParams
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
    """
    try:
        # Step 1: Initialize parameters and load data
        instrument_type = get_instrument_type(filename)
        resolution_type = "LOW" if instrument_type == "tof" else "HIGH"  # noqa: F841
        unmatched_defaults = UnmatchedIsotopeParams()

        # Filter isotopes below threshold and with incorrect resolution
        query = "relative_abundance >= @match_params.min_isotope_abundance and resolution == @resolution_type"
        target_isotopes_df = target_isotopes_df.query(query).reset_index(drop=True)

        # Step 2: - Detect peaks in the sample file
        peaks = await detect_and_load_peaks(
            filename=filename,
            instrument_type=instrument_type,
            instrument_functions=instrument_functions,
            target_mzs=target_isotopes_df.mz,
            polarity=polarity,
        )

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
            match_isotope_similarity=np.nan,
            match_mz_error=np.nan,
            match_score=unmatched_defaults.match_score,
            sample_peak_tof=np.nan,
        )

        # Step 4: Extract peak data for matching
        runtime.logger.debug("Parse peak data")

        parsed_peaks = parse_and_filter_peaks(peaks)

        # Step 5: Perform matching
        match_isotope_df = match_isotope_df.apply(
            match, args=(parsed_peaks,), axis=1
        ).reset_index()

        # Create a mask for matched isotopes (those with actual peak data)
        matched_mask = ~match_isotope_df["sample_peak_mz"].isna()

        # Step 6: - Calculate match stats for isotopes with actual matches
        if matched_mask.any():
            match_isotope_df = calculate_match_stats(match_isotope_df, peaks)

        # Step 7: Set default values for unmatched isotopes
        unmatched_mask = ~matched_mask
        if unmatched_mask.any():
            match_isotope_df = assign_defaults_to_unmatched(
                match_isotope_df, unmatched_mask
            )

        return match_isotope_df
    except Exception as e:
        error_message = f"Computing matches failed: {e}"
        runtime.logger.error(error_message)
        raise ValueError(error_message) from e


# --- Helper Functions ---


async def detect_and_load_peaks(
    filename: str,
    instrument_type: str,
    instrument_functions: tuple,
    target_mzs: pd.Series,
    polarity: Literal["+", "-"] | None = None,
):
    """Detect peaks in the sample file and load them into a DataArray.

    :param filename: Path to the sample file to be analyzed for matches.
    :type filename: str
    :param instrument_type: Type of the instrument used for the sample file, e.g., "orbi" or "tof".
    :type instrument_type: str
    :param instrument_functions: Tuple containing peak shape and a resolution function.
    :type instrument_functions: tuple
    :param target_mzs: Series of target m/z values to be matched against the sample peaks.
    :type target_mzs: pd.Series
    :param polarity: Polarity of the sample, either "+", "-", or "+-". Defaults to None.
    :type polarity: Literal["+", "-"], optional
    :return: DataArray containing detected peaks with their m/z, intensity, and time information.
    :rtype: xarray.DataArray
    """
    # Get list of nominal m/z values
    u_list = list(np.unique(np.round(target_mzs)))

    match instrument_type:
        case "orbi":
            peak_fit_threshold = ORBI_FITTING_THRESHOLD
        case "tof":
            peak_fit_threshold = TOF_FITTING_THRESHOLD

    # Detect peaks in the sample file
    await detect_peaks(
        filename,
        instrument_functions,
        peak_fit_threshold,
        u_list,
        if_exists="append",
        instrument_type=instrument_type,
    )

    runtime.logger.debug("Start matching")

    match instrument_type:
        case "orbi":
            peaks = load_array(filename, "peak_heights").peak_heights
        case "tof":
            peaks = load_array(filename, "peak_areas").peak_areas

    sample_file_type = get_sample_file_type(filename)
    if sample_file_type in ["orbi_zarr", "tof_zarr"]:
        peaks = peaks.dropna(dim="mz", how="all")

    if polarity:
        # Filter peaks based on polarity
        time_scan = get_scan_timestamps(filename, polarity=polarity)
        peaks = peaks.sel(time=time_scan, method="nearest")

    return peaks


def parse_and_filter_peaks(peaks: "xarray.DataArray") -> dict:  # type: ignore # noqa: F821
    """
    Parse and filter peaks from the detected peaks DataArray.

    :param peaks: Detected peaks DataArray containing m/z, intensity, and time information.
    :type peaks: xarray.DataArray
    :return: Dictionary containing parsed peak intensities, m/z values, and TOF values.
    :rtype: dict
    """
    peak_intensities = peaks.mean(dim="time").compute().values
    non_zero_peaks = peak_intensities > 0

    parsed_peaks = {
        "peak_intensities": peak_intensities[non_zero_peaks],
        "peak_mzs": peaks.mz.values[non_zero_peaks],
        "peak_tofs": peaks.tof.values[non_zero_peaks],
    }

    parsed_peaks["peak_sorting"] = np.argsort(parsed_peaks["peak_mzs"])

    return parsed_peaks


def match(row, parsed_peaks):
    """Match a target isotope with the closest peak in the sample spectrum.

    :param row: Row of the DataFrame containing target isotope properties.
    :type row: pd.Series
    :param parsed_peaks: Parsed peak data containing intensities, m/z values, and TOF values.
    :type parsed_peaks: dict
    :return: Row with matched peak information, including sample_peak_id, sample_peak_mz,
                sample_peak_tof, and sample_peak_intensity.
    :rtype: pd.Series
    """
    # Extract parsed peak data for ease of use
    peak_intensities = parsed_peaks["peak_intensities"]
    peak_mzs = parsed_peaks["peak_mzs"]
    peak_tofs = parsed_peaks["peak_tofs"]
    peak_sorting = parsed_peaks["peak_sorting"]

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


def calculate_match_stats(
    match_isotope_df: pd.DataFrame, peaks: "xarray.DataArray"  # type: ignore # noqa: F821
) -> pd.DataFrame:
    """Calculate match statistics for isotopes.

    :param match_isotope_df: DataFrame containing matched isotopes with their properties.
    :type match_isotope_df: pd.DataFrame
    :param peaks: Detected peaks DataArray containing m/z, intensity, and time information.
    :type peaks: xarray.DataArray
    :return: DataFrame with match statistics for each isotope, including relative peak intensities,
              abundance matching errors, isotope similarities, m/z errors, and match scores.
    :rtype: pd.DataFrame
    """
    ion_level_peak_sums = match_isotope_df.groupby("target_ion_id", as_index=False)[
        "sample_peak_intensity"
    ].sum()

    # Join sums back to the isotope level
    isotope_level_peak_sums = pd.merge(
        match_isotope_df,
        ion_level_peak_sums.rename(
            columns={"sample_peak_intensity": "sample_peak_intensity_sum"}
        ),
        on="target_ion_id",
        how="left",
    )

    match_isotope_df.loc[:, "sample_peak_intensity_relative"] = (
        match_isotope_df["sample_peak_intensity"]
        / isotope_level_peak_sums["sample_peak_intensity_sum"]
    )

    match_isotope_df.loc[:, "match_abundance_error"] = match_isotope_df[
        "relative_abundance"
    ] * (
        match_isotope_df["sample_peak_intensity_relative"]
        - match_isotope_df["relative_abundance"]
    )

    # Calculate isotope similarities by ion group
    match_isotope_df = match_isotope_df.groupby(
        ["target_ion_id"], group_keys=False
    ).apply(assign_isotope_similarity, peaks=peaks)

    match_isotope_df["match_isotope_similarity"] = match_isotope_df[
        "match_isotope_similarity"
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

    match_isotope_df = match_isotope_df.apply(score, axis=1, result_type="broadcast")

    return match_isotope_df


def assign_isotope_similarity(ion_group, peaks):
    """
    Assign isotope similarity to a group of isotopes

    :param ion_group: Group of isotopes sharing the same target ion ID.
    :type ion_group: pd.DataFrame
    :param peaks: Detected peaks DataArray containing m/z, intensity, and time information.
    :type peaks: xarray.DataArray
    :return: Group of isotopes with an additional column for match_isotope_similarity.
    :rtype: pd.DataFrame
    """
    if len(ion_group) > 1:
        similarity = mean_cosine_similarity(
            np.array(
                [
                    peaks.sel(mz=peak_mz, method="nearest")
                    for peak_mz in ion_group["sample_peak_mz"]
                ]
            )
        )
    else:
        similarity = 1.0
    ion_group = ion_group.assign(match_isotope_similarity=similarity)
    return ion_group


def assign_defaults_to_unmatched(
    match_isotope_df: pd.DataFrame,
    unmatched_mask: pd.Series,
) -> pd.DataFrame:
    """
    Assign default values to unmatched isotopes in the match DataFrame.

    This function sets default values for isotopes that did not find a matching peak,
    ensuring that all required fields are populated with appropriate defaults.

    :param match_isotope_df: DataFrame containing matched isotopes with their properties.
    :type match_isotope_df: pd.DataFrame
    :param unmatched_mask: Boolean mask indicating which isotopes do not have matching peaks.
    :type unmatched_mask: pd.Series
    :return: DataFrame with default values assigned to unmatched isotopes.
    :rtype: pd.DataFrame
    """
    unmatched_defaults = UnmatchedIsotopeParams()
    unmatched_count = unmatched_mask.sum()
    runtime.logger.info(f"Found {unmatched_count} isotopes without matching peaks")

    # Set sample_peak_mz for unmatched isotopes using target m/z values
    match_isotope_df.loc[unmatched_mask, "sample_peak_mz"] = match_isotope_df.loc[
        unmatched_mask, "mz"
    ]

    # Apply all defaults except sample_peak_mz which was handled above
    for column, value in unmatched_defaults.model_dump().items():
        if column != "sample_peak_mz":
            match_isotope_df.loc[unmatched_mask, column] = value

    return match_isotope_df


def mean_cosine_similarity(arr: np.ndarray) -> float:
    """
    Calculate mean cosine similarity.

    This function computes the pairwise cosine distances between vectors in a 2D array
    and returns the mean cosine similarity of the upper triangle of the similarity matrix.
    :param arr: 2D array where each row is a vector (e.g., isotope profiles)
    :type arr: np.ndarray
    :return: Mean cosine similarity of the upper triangle of the similarity matrix
    :rtype: float
    """
    n = arr.shape[0]
    if n < 2:
        return 1.0

    distances = pdist(arr, "cosine")
    return 1.0 - distances.mean()
