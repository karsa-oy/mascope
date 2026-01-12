from typing import Literal
import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist

import mascope_file.io as m_io
import mascope_signal.compute as m_compute
from mascope_file.name import get_instrument_type, get_sample_file_type
from mascope_match.runtime import runtime

from mascope_match.params import unmatched_isotope_params, BaseMatchParams
from mascope_match.id import generate_id

MATCH_WINDOW_AMU = 0.5  # Da


async def compute_match_isotopes(
    filename: str,
    target_isotopes_df: pd.DataFrame,
    match_params: BaseMatchParams | None = None,
    polarity: Literal["+", "-"] | None = None,
) -> pd.DataFrame:
    """
    Compute matches between target isotopes and sample file peaks.

    This function identifies the best matching peaks within the sample spectrum for each target isotope
    based on their m/z values and computes match statistics. For isotopes without matching peaks,
    default values are assigned with a match score of 0.

    Steps:
    - Apply filtering only if match_params provided (backwards compatibility)
    - Load sample peaks
    - Initialize match DataFrame with placeholders for all target isotopes
    - Extract peak data and perform matching
    - Calculate match stats and assign defaults for unmatched isotopes
    - Return a DataFrame containing match details for all target isotopes

    :param filename: Path to the sample file to be analyzed for matches.
    :type filename: str
    :param target_isotopes_df: DataFrame containing target isotopes with their m/z values and other properties.
    :type target_isotopes_df: pd.DataFrame
    :param match_params: Match parameters containing settings for the matching process, default to None
    :type match_params: BaseMatchParams | None
    :param polarity: Polarity of the sample, either "+" or "-".
    :type polarity: Literal["+", "-"], optional
    :return: DataFrame with match details for all target isotopes, including those without matches
    :rtype: pd.DataFrame
    :raises ValueError: If an error occurs during the matching process.

    Notes:
    - Matching is done at the isotope level. Ion, compound and collection level matches are
      aggregated in a separate process.
    - Isotopes without matching peaks are assigned a match score of 0 and placeholder values
      for the required database fields.
    - Supports both database-pre-filtered isotopes (when match_params=None)
      and legacy filtering (when match_params provided for backwards compatibility).
      TODO remove match_params and target isotopes filtering form here? keep only actual computing
    """
    runtime.logger.debug("Start matching...")
    try:
        # --- Apply filtering only if match_params provided (backwards compatibility) ---
        instrument_type = get_instrument_type(filename)
        if match_params is not None:
            # Filter isotopes below threshold and with incorrect resolution
            resolution_type = (  # noqa: F841
                "LOW" if instrument_type == "tof" else "HIGH"
            )
            query = "relative_abundance >= @match_params.min_isotope_abundance and resolution == @resolution_type"
            target_isotopes_df = target_isotopes_df.query(query).reset_index(drop=True)
        else:
            runtime.logger.debug("Using database-pre-filtered target isotopes")

        if target_isotopes_df.empty:
            runtime.logger.debug("No target isotopes to process")
            return pd.DataFrame()

        # --- Load sample peaks ---
        peaks = await load_peaks(
            filename=filename,
            target_mzs=target_isotopes_df.mz,
            polarity=polarity,
        )

        # --- Initialize match DataFrame with placeholders for all target isotopes ---
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
            match_score=unmatched_isotope_params.match_score,
            sample_peak_tof=np.nan,
        )
        match_isotope_df["sample_peak_id"] = match_isotope_df["sample_peak_id"].astype(
            "object"
        )

        # --- Extract peak data and perform matching ---
        runtime.logger.debug("Parse peak data")
        parsed_peaks = parse_and_filter_peaks(peaks)
        runtime.logger.debug("Perform isotope matching")
        match_isotope_df = _match_assign(match_isotope_df, parsed_peaks)

        # --- Calculate match stats and assign defaults for unmatched isotopes ---
        # Create a mask for matched isotopes (those with actual peak data)
        matched_mask = ~match_isotope_df["sample_peak_mz"].isna()

        # Calculate match stats for isotopes with actual matches
        if matched_mask.any():
            runtime.logger.debug("Calculate match statistics for matched isotopes")
            match_isotope_df = calculate_match_stats(match_isotope_df, peaks)

        # Set default values for unmatched isotopes
        unmatched_mask = ~matched_mask
        if unmatched_mask.any():
            runtime.logger.debug("Assign default values to unmatched isotopes")
            match_isotope_df = assign_defaults_to_unmatched(
                match_isotope_df, unmatched_mask
            )

        # Drop helper column
        match_isotope_df.drop(columns=["closest_peak_idx"], inplace=True)

        # --- Return a DataFrame containing match details for all target isotopes ---
        return match_isotope_df
    except Exception as e:
        error_message = f"Computing matches failed: {e}"
        runtime.logger.error(error_message)
        raise ValueError(error_message) from e


async def load_peaks(
    filename: str,
    target_mzs: pd.Series,
    polarity: Literal["+", "-"] | None = None,
):
    """Loads target_mzs peak timeseries of required polarity from the sample file.
    Loads peak_heights for Orbitrap files and peak_areas for TOF files.

    :param filename: Path to the sample file to be analyzed for matches.
    :type filename: str
    :param target_mzs: Series of target m/z values to be matched against the sample peaks.
    :type target_mzs: pd.Series
    :param polarity: Polarity of the sample, either "+", "-", or "+-". Defaults to None.
    :type polarity: Literal["+", "-"], optional
    :return: DataArray containing detected peaks with their m/z, intensity, and time information.
    :rtype: xarray.DataArray
    """
    instrument_type = get_instrument_type(filename)
    target_mzs = np.asarray(target_mzs)
    peak_data = m_io.load_peak_data(filename)
    # Select unique closest m/z values from the peak data
    closest_mzs = peak_data.sel(mz=target_mzs, method="nearest").mz.values
    closest_mzs = np.unique(closest_mzs)

    # Compute all peak timeseries within MATCH_WINDOW_AMU of target m/z values
    # to not compute them later in Match tab visualization
    all_mzs = peak_data.mz.values
    mz_mask = np.any(
        np.abs(all_mzs[:, None] - closest_mzs[None, :]) <= MATCH_WINDOW_AMU, axis=1
    )
    mz_to_compute = all_mzs[mz_mask]

    peak_timeseries = await m_compute.load_peak_timeseries(filename, mz_to_compute)
    # Narrow down to closest m/z values only after computing peak timeseries
    peak_timeseries = peak_timeseries.sel(mz=closest_mzs)

    match instrument_type:
        case "orbi":
            peaks = peak_timeseries.peak_heights
        case "tof":
            peaks = peak_timeseries.peak_areas

    sample_file_type = get_sample_file_type(filename)
    if sample_file_type in ["orbi_zarr", "tof_zarr"]:
        peaks = peaks.dropna(dim="mz", how="all")

    if polarity:
        # Filter peaks based on polarity
        time_scan = m_compute.get_scan_timestamps(filename, polarity=polarity)
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
    peak_intensities = peaks.mean(dim="time").values
    non_zero_peaks = peak_intensities > 0

    parsed_peaks = {
        "peak_intensities": peak_intensities[non_zero_peaks],
        "peak_mzs": peaks.mz.values[non_zero_peaks],
        "peak_ids": peaks.peak_id.values[non_zero_peaks],
        "peak_tofs": peaks.tof.values[non_zero_peaks],
    }

    parsed_peaks["peak_sorting"] = np.argsort(parsed_peaks["peak_mzs"])

    return parsed_peaks


def _match_assign(match_isotope_df: pd.DataFrame, parsed_peaks: dict) -> pd.DataFrame:
    """Match target isotopes with the closest peak in the sample spectrum.

    :param match_isotope_df: DataFrame containing target isotope properties.
    :type match_isotope_df: pd.DataFrame
    :param parsed_peaks: Parsed peak data containing intensities, m/z values, and TOF values.
    :type parsed_peaks: dict
    :return: DataFrame with matched peak information
    :rtype: pd.DataFrame
    """
    peak_mzs = np.asarray(parsed_peaks["peak_mzs"])
    peak_sorting = np.asarray(parsed_peaks["peak_sorting"])
    sorted_mzs = peak_mzs[peak_sorting]

    target_mzs = match_isotope_df["mz"].values

    # nearest neighbor in sorted_mzs
    insertion_positions = np.searchsorted(sorted_mzs, target_mzs)
    insertion_positions = np.clip(insertion_positions, 1, len(sorted_mzs) - 1)
    left_insert_index = insertion_positions - 1
    right_insert_index = insertion_positions

    is_right_closer = np.abs(sorted_mzs[right_insert_index] - target_mzs) < np.abs(
        sorted_mzs[left_insert_index] - target_mzs
    )
    nearest_neighbor_indices = np.where(
        is_right_closer, right_insert_index, left_insert_index
    )
    nearest_neighbor_difference = np.abs(
        sorted_mzs[nearest_neighbor_indices] - target_mzs
    )

    is_within_tolerance = nearest_neighbor_difference <= MATCH_WINDOW_AMU
    closest_peak_index = peak_sorting[nearest_neighbor_indices]

    # Assign only for matches
    match_isotope_df.loc[is_within_tolerance, "sample_peak_id"] = np.array(
        parsed_peaks["peak_ids"]
    )[closest_peak_index[is_within_tolerance]]
    match_isotope_df.loc[is_within_tolerance, "sample_peak_mz"] = peak_mzs[
        closest_peak_index[is_within_tolerance]
    ].astype(float)
    match_isotope_df.loc[is_within_tolerance, "sample_peak_tof"] = np.asarray(
        parsed_peaks["peak_tofs"]
    )[closest_peak_index[is_within_tolerance]]
    match_isotope_df.loc[is_within_tolerance, "sample_peak_intensity"] = np.asarray(
        parsed_peaks["peak_intensities"]
    )[closest_peak_index[is_within_tolerance]]

    # Store closest peak index as a helper for later calculations, will be dropped later
    match_isotope_df.loc[is_within_tolerance, "closest_peak_idx"] = closest_peak_index[
        is_within_tolerance
    ]
    match_isotope_df["closest_peak_idx"] = match_isotope_df["closest_peak_idx"].astype(
        "Int64"
    )

    return match_isotope_df


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

    # Step 1: Collect abundance and intensity reference values
    ## Find the rows with maximum relative_abundance per target ion; "main isotopes"
    idx_max_abundance = (
        match_isotope_df.groupby("target_ion_id")["relative_abundance"].idxmax().values
    )
    ## Get the sample_peak_intensity values for the main isotopes
    main_isotope_df = match_isotope_df.loc[
        idx_max_abundance,
        ["target_ion_id", "sample_peak_intensity", "relative_abundance"],
    ].reset_index(drop=True)
    ## Join the main isotopes with the full match_isotope_df to get the reference values
    abundance_reference_df = pd.merge(
        match_isotope_df,
        main_isotope_df.rename(
            columns={
                "sample_peak_intensity": "sample_peak_intensity_reference",
                "relative_abundance": "relative_abundance_reference",
            }
        ),
        on="target_ion_id",
        how="left",
    )
    # Step 2: Compute match abundance error
    ## Compute relative peak intensities -> [0, 1]
    match_isotope_df.loc[:, "sample_peak_intensity_relative"] = (
        match_isotope_df["sample_peak_intensity"]
        / abundance_reference_df["sample_peak_intensity_reference"]
    ).fillna(0.0)
    ## Normalize relative abundances by the main isotope's relative abundance -> [0, 1]
    match_isotope_df.loc[:, "relative_abundance_norm"] = (
        match_isotope_df["relative_abundance"]
        / abundance_reference_df["relative_abundance_reference"]
    )
    ## Calculate abundance error as relative difference
    match_isotope_df.loc[:, "match_abundance_error"] = (
        match_isotope_df["sample_peak_intensity_relative"]
        / match_isotope_df["relative_abundance_norm"]
        - 1.0
    )
    match_isotope_df.drop(columns=["relative_abundance_norm"], inplace=True)

    # Step 3: Calculate isotope similarities by ion group
    match_isotope_df = match_isotope_df.groupby(["target_ion_id"], group_keys=False)[
        match_isotope_df.columns
    ].apply(assign_isotope_similarity, peaks=peaks)

    match_isotope_df["match_isotope_similarity"] = match_isotope_df[
        "match_isotope_similarity"
    ].fillna(0.0)

    # Step 4: Calculate m/z errors (in ppm)
    match_isotope_df.loc[:, "match_mz_error"] = (
        1e6
        * (match_isotope_df["sample_peak_mz"] - match_isotope_df["mz"])
        / match_isotope_df["mz"]
    )

    # Step 5: Calculate match scores
    abundance_term = 1.0 - np.minimum(
        1.0, np.abs(match_isotope_df["match_abundance_error"].values)
    )
    mz_term = np.maximum(
        0.0, 1.0 - 1e-2 * np.abs(match_isotope_df["match_mz_error"].values)
    )
    match_isotope_df["match_score"] = abundance_term * mz_term

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
        peak_indices = ion_group["closest_peak_idx"].values
        closest_timeseries = peaks.isel(mz=peak_indices).values
        similarity = mean_cosine_similarity(closest_timeseries)
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
    unmatched_count = unmatched_mask.sum()
    runtime.logger.info(f"Found {unmatched_count} isotopes without matching peaks")

    # Set sample_peak_mz for unmatched isotopes using target m/z values
    match_isotope_df.loc[unmatched_mask, "sample_peak_mz"] = match_isotope_df.loc[
        unmatched_mask, "mz"
    ]

    # Apply all defaults except sample_peak_mz which was handled above
    for column, value in unmatched_isotope_params.model_dump().items():
        if column != "sample_peak_mz":
            match_isotope_df.loc[unmatched_mask, column] = value

    return match_isotope_df


def mean_cosine_similarity(arr: np.ndarray) -> float:
    """
    Calculate mean cosine similarity.

    This function computes the pairwise cosine distances between vectors in a 2D array
    and returns the mean cosine similarity of the upper triangle of the similarity matrix.
    :param arr: 2D array where each row is a vector (e.g., isotope timeseries)
    :type arr: np.ndarray
    :return: Mean cosine similarity of the upper triangle of the similarity matrix
    :rtype: float
    """
    n = arr.shape[0]
    if n < 2:
        return 1.0

    distances = pdist(arr, "cosine")
    return 1.0 - distances.mean()
