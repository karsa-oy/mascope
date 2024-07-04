# -------------------------------------------------------------------
# Imports
# -------------------------------------------------------------------
from typing import List, Optional
import pandas as pd
import numpy as np
from mascope_lib.file_func import get_instrument_type, get_sum_signal
from mascope_lib.peak import detect_peaks, get_peaks
from mascope_lib.chemistry import match_mz
from mascope_server.db.id import gen_id
from mascope_server.api.utils.api_features import (
    api_controller,
    send_progress_user_notification,
)
from mascope_server.api.controllers.match.util import (
    fetch_targets_for_match_remove,
)
from mascope_server.api.controllers.match.match_isotopes_controller import (
    get_match_isotopes,
    create_match_isotopes,
    delete_match_isotopes,
)
from mascope_server.api.controllers.match.match_interferences_controller import (
    get_match_interferences,
    create_match_interferences,
    delete_match_interferences,
)
from mascope_server.api.controllers.instrument_functions_controller import (
    read_instrument_functions,
)
from mascope_server.api.controllers.match.match_ions_controller import (
    delete_match_ions,
)
from mascope_server.api.controllers.match.match_compounds_controller import (
    delete_match_compounds,
)
from mascope_server.api.controllers.match.match_collections_controller import (
    delete_match_collections,
)
from mascope_server.api.controllers.match.match_samples_controller import (
    delete_match_samples,
)
from mascope_server.api.models.pydantic_models.match_pydantic_model import (
    FilterParams,
    MatchComputeSample,
)
from mascope_server.api.models.pydantic_models.match_interferences_pydantic_model import (
    MatchInterferenceBase,
)
from mascope_server.api.models.pydantic_models.match_isotopes_pydantic_model import (
    MatchIsotopeBase,
)
from mascope_server.api.models.pydantic_models.user_notification_pydantic_model import (
    UserNotification,
)

# TODO_configuration
# Default Filter Parameters
DEFAULT_MIN_ISOTOPE_ABUNDANCE = 0.15

# -------------------------------------------------------------------
# Main Logic Functions
# -------------------------------------------------------------------


@api_controller()
async def compute_and_create_sample_match_isotope_data(
    sample: MatchComputeSample,
    target_isotopes_df,
    notification: UserNotification = None,
):
    """
    Computes matc isotopes and match interferences for a given sample against a set of target isotopes.

    It updates the computation progress if progress properties are provided. Match isotopes and interferences are then saved to the database.

    Steps:
    1. Unpack sample parameters including sample item ID and filename.
    2. Compute match interferences for the sample using the provided target isotopes.
    3. Compute match isotopes for the sample using the provided target isotopes.
    4. Save computed match interferences and match isotopes to the database, ensuring no duplication.
    5. Update computation progress at each significant step if progress tracking is enabled.

    :param sample: Contains details of the sample for which match isotopes are being computed, including sample item ID and filename.
    :type sample: MatchComputeSample
    :param target_isotopes_df: A DataFrame containing target isotope information for match computation.
    :type target_isotopes_df: DataFrame
    :param notification: Optional notification for sending progress user notifications of match computation.
    :type notification: UserNotification, optional
    :raises RuntimeError: If no match interferences or match isotopes are found during computation.
    """
    # Step 1: Unpack the sample parameters for ease of use
    sample_item_id = sample.sample_item_id
    filename = sample.filename

    #  Sent progress user notificaton if notification is provided
    if notification:
        await send_progress_user_notification(notification, 0.25)

    # Step 2: Compute match interferences for the given sample and target isotopes.
    print("Computing match interferences for file: %s" % filename)
    match_interference_df = await compute_match_interferences(
        filename, target_isotopes_df
    )
    if match_interference_df.empty:
        raise RuntimeError("No match interferences found")
    # Send progress user notificaton after computing interferences
    if notification:
        await send_progress_user_notification(notification, 0.5)

    # Step 3: Compute match isotopes for the given sample and target isotopes.
    print("Computing match isotopes for file: %s" % filename)
    match_isotope_df = await compute_match_isotopes(
        filename=filename,
        target_isotopes_df=target_isotopes_df,
        min_isotope_abundance=DEFAULT_MIN_ISOTOPE_ABUNDANCE,
    )
    if match_isotope_df.empty:
        raise RuntimeError("No match isotopes found")
    # Send progress user notificaton after computing match isotopes
    if notification:
        await send_progress_user_notification(notification, 0.75)

    # Step 4: Save to the database computed match interferences and isotopes if any were found
    match_interference_df["sample_item_id"] = sample_item_id
    match_isotope_df["sample_item_id"] = sample_item_id

    # Convert the DataFrame to a list of Pydantic models
    match_interferences = [
        MatchInterferenceBase(**row)
        for row in match_interference_df.to_dict(orient="records")
    ]
    match_isotopes = [
        MatchIsotopeBase(**row) for row in match_isotope_df.to_dict(orient="records")
    ]

    await create_match_interferences(match_interferences)
    await create_match_isotopes(match_isotopes)

    # Send progress user notificaton indicating completion of compute_and_create_sample_match_isotope_data process
    if notification:
        await send_progress_user_notification(notification, 0.95)


# -------------------------------------------------------------------
# Isotope level
# -------------------------------------------------------------------


async def compute_match_isotopes(
    filename, target_isotopes_df, min_isotope_abundance, instrument_functions=None
):
    """
    Computes matches for specified target isotopes within a sample file.

    This function identifies the best matching peaks within the sample spectrum for each target isotope based on
    their m/z values. It computes match statistics such as match score, m/z error, and isotope correlation.

    Steps:
    1. Load peaks from the sample file and prepare the data for matching.
    2. MatchIsotope each target isotope to the closest peak within a predefined m/z tolerance window.
    3. Compute match statistics such as isotope correlations, m/z errors, and match score.
    4. Return a DataFrame containing the match details for each target isotope.

    :param filename: Path to the sample file to be analyzed for matches.
    :type filename: str
    :param target_isotopes_df: DataFrame containing target isotopes with their m/z values and other properties.
    :type target_isotopes_df: pd.DataFrame
    :param min_isotope_abundance: Minimum relative abundance threshold for isotopes to be considered in matching.
    :type min_isotope_abundance: float
    :param instrument_functions: Optional tuple containing peak shape details and a resolution function R.
    :type instrument_functions: tuple(dict, function), optional
    :return: DataFrame with details of the matches found for each target isotope.
    :rtype: pd.DataFrame
    :raises RuntimeError: If an error occurs during the matching process.

    Notes:
        - Matching is done on isotope-level. Ion, compound and collection level matches are aggregated from
        isotope-level matches on read sample operation; see the samples_controller.py for this aggregation.
    """
    try:
        # TODO min_isotope_abundance will be passed from the filter_params
        target_isotopes_df = target_isotopes_df[
            target_isotopes_df["relative_abundance"] >= min_isotope_abundance
        ].reset_index(drop=True)

        # Step 1: - Load or detect peaks
        # Find peaks and write to file
        u_list = list(np.unique(np.round(target_isotopes_df.mz)))
        # Check if instrument functions were passed
        if instrument_functions is None:
            instrument_functions = await read_instrument_functions(filename)
        instrument_type = get_instrument_type(filename)
        # Assign peak fitting threshold depending on the instrument type
        # Correct intrument type unsured by get_instrument_type
        if instrument_type == "orbi":
            threshold = 0.8
        if instrument_type == "tof":
            threshold = 0.9
        sample_file = await detect_peaks(
            filename,
            instrument_functions,
            threshold,
            u_list,
            if_exists="append",
            instrument_type=instrument_type,
        )
        peaks = get_peaks(sample_file, "area")

        # Step 2: - Prepare data
        # init match df from target isotopes
        match_isotope_df = target_isotopes_df.copy().assign(
            match_isotope_id=np.nan,
            sample_peak_id=np.nan,
            sample_peak_mz=np.nan,
            sample_peak_area=np.nan,
            sample_peak_area_relative=np.nan,
            match_abundance_error=np.nan,
            match_isotope_correlation=np.nan,
            match_mz_error=np.nan,
            match_score=np.nan,
        )

        # parse peak data
        peak_mzs = peaks.mz.values
        peak_areas = peaks.sum(dim="time").values
        peak_tofs = peaks.tof.values
        peak_sorting = np.argsort(peak_mzs)

        # Step 3: - Perform matching

        def match(row):
            # Get all peaks within unit mass window
            mz_tolerance = 0.5
            target_mz = row.mz
            match_indeces, _ = match_mz(
                target_mz, peak_mzs[peak_sorting], tolerance=mz_tolerance
            )
            # Find closest match
            for match_index in match_indeces:
                # get match peak
                peak_index = peak_sorting[match_index]
                peak_mz = peak_mzs[peak_index]
                peak_area = peak_areas[peak_index]
                # check current best match
                best_match = row.sample_peak_id
                if not np.isnan(best_match):
                    prev_mz_err = np.abs(row.sample_peak_mz - target_mz)
                    new_mz_err = np.abs(peak_mz - target_mz)
                    if new_mz_err > prev_mz_err:
                        continue
                # save match
                row["match_isotope_id"] = gen_id(length=32)
                row["sample_peak_id"] = peak_index
                row["sample_peak_mz"] = peak_mz
                row["sample_peak_tof"] = peak_tofs[int(peak_index)]
                row["sample_peak_area"] = peak_area
            return row

        match_isotope_df = (
            match_isotope_df.apply(match, axis=1)
            .dropna(subset=["sample_peak_mz"])
            .reset_index()
        )

        # Step 4: - Calculate match stats

        # calculate isotope ratios
        # sum matched sample peak heights for each ion
        ion_level_peak_sums = match_isotope_df.groupby(
            ["target_ion_id"], as_index=False
        )["sample_peak_area"].sum()
        # join sums back to the isotope level
        isotope_level_peak_sums = pd.merge(
            match_isotope_df,
            ion_level_peak_sums.rename(
                columns={"sample_peak_area": "sample_peak_area_sum"}
            ),
            on=["target_ion_id"],
            how="left",
        )

        # compute relative peak heights
        match_isotope_df.loc[:, "sample_peak_area_relative"] = (
            match_isotope_df["sample_peak_area"]
            / isotope_level_peak_sums["sample_peak_area_sum"]
        )
        # calculate isotope ratio errors
        match_isotope_df.loc[:, "match_abundance_error"] = match_isotope_df[
            "relative_abundance"
        ] * (
            match_isotope_df["sample_peak_area_relative"]
            - match_isotope_df["relative_abundance"]
        )
        # calculate isotope correlations
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
        ].fillna(value=0)

        # calculate mz errors
        match_isotope_df.loc[:, "match_mz_error"] = (
            1e6
            * (match_isotope_df["sample_peak_mz"] - match_isotope_df["mz"])
            / match_isotope_df["mz"]
        )

        def score(row):
            row["match_score"] = (1 - abs(row.match_abundance_error)) * max(
                0, (1 - 1e-2 * abs(row.match_mz_error))
            )
            return row

        match_isotope_df = match_isotope_df.apply(
            score, axis=1, result_type="broadcast"
        )
        return match_isotope_df
    except Exception as e:
        error_message = f"Computing matches failed: {e}"
        raise RuntimeError(error_message)


async def compute_match_interferences(
    filename,
    target_isotopes_df,
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
    :return: DataFrame with computed interferences for each target isotope.
    :rtype: pd.DataFrame
    :raises RuntimeError: If an error occurs during the computation process.
    """
    try:
        # Step 1: Load the sample file and compute the summed spectrum
        sum_spectrum = get_sum_signal(filename)

        # Read instrument resolution function
        _, R = await read_instrument_functions(filename)

        # Step 2: Initialize DataFrame for interferences and compute raw intensities for each target mz
        isotope_interference_df = target_isotopes_df.copy().assign(
            sample_peak_interference=np.nan,
        )

        def calc_raw_intensity(row):
            target_mz = row.mz
            dmz = (target_mz / R(target_mz)) / 2  # hwhm
            target_raw_intensity = sum_spectrum.sel(
                mz=slice(target_mz - dmz, target_mz + dmz)
            ).sum(dim="mz")
            row["match_interference_id"] = gen_id(length=32)
            row["sample_peak_interference"] = target_raw_intensity.compute().item()
            return row

        isotope_interference_df = isotope_interference_df.apply(
            calc_raw_intensity, axis=1
        )

        return isotope_interference_df
    except Exception as e:
        error_message = f"Computing match interferences failed: {e}"
        raise RuntimeError(error_message)


@api_controller()
async def remove_matches(
    sample_item_id: Optional[str] = None,
    sample_batch_id: Optional[str] = None,
    removed_target_compound_ids: Optional[List[str]] = None,
    removed_ionization_mechanism_ids: Optional[List[str]] = None,
    match_interferences: Optional[bool] = True,
    match_isotopes: Optional[bool] = True,
    match_ions: Optional[bool] = True,
    match_compounds: Optional[bool] = True,
    match_collections: Optional[bool] = True,
    match_samples: Optional[bool] = True,
) -> dict:
    """
    Removes all match data associated with specified sample items or a sample batch.
    This operation can target a specific sample item or all items within a specified batch.

    Steps:
    1. Fetch sample item IDs using the utility function.
    2. Execute deletion operations for all match data types using the resolved sample item IDs.
    3. Compile messages from each deletion operation and report back.

    :param sample_item_id: ID of the single sample item for which matches are to be removed, optional.
    :param sample_batch_id: ID of the sample batch from which sample items are derived for deletion, optional.
    :return: A dictionary with a message and log of actions taken.
    """
    # Step 1: Determine the target IDs that are associated with the removed compounds or ionization mechanisms.
    targets = {
        "target_isotope_ids": [],
        "target_ion_ids": [],
        # "target_compound_ids": [],
    }
    filtered_targets_message = ""
    if removed_target_compound_ids or removed_ionization_mechanism_ids:
        targets = await fetch_targets_for_match_remove(
            removed_target_compound_ids, removed_ionization_mechanism_ids
        )
        filtered_targets_message = "Associated with:"
        if removed_target_compound_ids:
            filtered_targets_message += (
                f" {len(removed_target_compound_ids)} removed compound(s)."
            )
        if removed_ionization_mechanism_ids:
            filtered_targets_message += f" {len(removed_ionization_mechanism_ids)} removed ionization mechanism(s)."
    # Step 2: Delete matches corresponding to these targets.
    # List of operations including function references, description, and a dictionary of parameters
    delete_operations = []
    descriptions = []
    if match_interferences:
        delete_operations.append(
            (
                delete_match_interferences,
                "match_interferences",
                {"target_isotope_ids": targets["target_isotope_ids"]},
            )
        )
        descriptions.append("match_interferences")
    if match_isotopes:
        delete_operations.append(
            (
                delete_match_isotopes,
                "match_isotopes",
                {"target_isotope_ids": targets["target_isotope_ids"]},
            )
        )
        descriptions.append("match_isotopes")
    if match_ions:
        delete_operations.append(
            (
                delete_match_ions,
                "match_ions",
                {"target_ion_ids": targets["target_ion_ids"]},
            )
        )
        descriptions.append("match_ions")
    if match_compounds:
        delete_operations.append(
            (
                delete_match_compounds,
                "match_compounds",
                {},
            )
        )
        descriptions.append("match_compounds")
    if match_collections:
        delete_operations.append((delete_match_collections, "match_collections", {}))
        descriptions.append("match_collections")
    if match_samples:
        delete_operations.append((delete_match_samples, "match_samples", {}))
        descriptions.append("match_samples")

    delete_matches_message = (
        "all matches" if len(descriptions) == 6 else ", ".join(descriptions)
    )
    print(f"Removing {delete_matches_message}. {filtered_targets_message}")

    message_logs = []
    for delete_func, description, params in delete_operations:
        # Injecting common sample id parameter
        if sample_batch_id:
            params["sample_batch_id"] = sample_batch_id
        if sample_item_id:
            params["sample_item_id"] = sample_item_id
        result = await delete_func(**params)
        message_logs.append(f"{description}: {result['message']}")

    message = (
        f"Removed successfully {delete_matches_message}. {filtered_targets_message}"
    )
    return {
        "message": message,
        "message_logs": message_logs,
    }


async def filter_existing_sample_match_isotope_data(target_isotopes_df, sample_item_id):
    """
    Filters out target isotopes for a given sample item that already have matches or match interferences,
    ensuring that only isotopes without existing matches are considered for new match computation.

    This function checks existing matches and match interferences for the given sample item and
    excludes those target isotopes from the provided DataFrame that already have matches or interferences.
    This helps in optimizing the match computation process by avoiding redundant calculations for isotopes
    that already have matches.

    Steps:
    1. Retrieve existing matches and match interferences for the specified sample item.
    2. Identify target isotope IDs from existing matches and interferences.
    3. Filter out these isotopes from the provided DataFrame to exclude already matched isotopes.
    4. Return the filtered DataFrame, ready for further match computation processes.

    :param target_isotopes_df: DataFrame containing target isotopes to be considered for match computation.
    :type target_isotopes_df: pandas.DataFrame
    :param sample_item_id: Unique identifier of the sample item for which existing matches and interferences are to be checked.
    :type sample_item_id: str
    :raises RuntimeError: Raises an error if the process of fetching existing matches or interferences, or filtering fails.
    :return: A filtered DataFrame excluding isotopes that already have matches or interferences.
    :rtype: pandas.DataFrame
    """
    try:
        # Step 1: Fetch existing matches and interferences for the given sample item.
        existing_match_isotopes = await get_match_isotopes(
            sample_item_id=sample_item_id
        )
        existing_interferences = await get_match_interferences(
            sample_item_id=sample_item_id
        )

        # Step 2: Compile sets of target isotope IDs from existing matches and interferences.
        existing_match_isotopes_ids = {
            match["target_isotope_id"] for match in existing_match_isotopes["data"]
        }
        existing_interference_ids = {
            interference["target_isotope_id"]
            for interference in existing_interferences["data"]
        }

        # Step 3: Filter out isotopes from the DataFrame that already have matches or interferences.
        target_isotopes_df = target_isotopes_df[
            ~target_isotopes_df["target_isotope_id"].isin(
                existing_match_isotopes_ids | existing_interference_ids
            )
        ]

        # Step 4: Return the filtered DataFrame, which now only contains isotopes without existing matches or interferences.
        return target_isotopes_df
    except Exception as e:
        error_message = f"Filtering existing matches and interferences failed: {e}"
        raise RuntimeError(error_message)


def apply_filter_params(match_isotope_df, filter_params: FilterParams = None):
    """
    Apply filtering logic to a isotope-lvl matches DataFrame.

    :param match_isotope_df: DataFrame containing match isotope data.
    :type match_isotope_df: pd.DataFrame
    :param filter_params: Optional; Pydantic model of filtering parameters.
    :type filter_params: FilterParams
    :return: DataFrame with applied filters.
    :rtype: pd.DataFrame
    """
    # Convert filter_params Pydantic model to dictionary if provided
    provided_params = filter_params.dict() if filter_params else None

    def get_params(row):
        """
        Determine the filter parameters to use based on the priority:
        1. Provided filter parameters
        2. Ion-specific filter parameters for the sample instrument
        3. Default filter parameters
        """
        # If provided_params are available, use them for all rows
        if provided_params:
            return provided_params

        # If row-specific filter_params are available for the instrument, use them
        if "filter_params" in row and row["instrument"] in row["filter_params"]:
            return row["filter_params"][row["instrument"]]

        # Define default filter parameters from the FilterParams Pydantic model
        default_params = FilterParams().dict()
        # Fallback to default parameters
        return default_params

    def filter_row(row):
        """
        Apply filtering logic to the given row based on the determined parameters.
        """
        # Determine which filter parameters to use for the current row
        params = get_params(row)

        # Apply filtering logic
        row["match_score"] = (
            row["match_score"]
            if all(
                [
                    abs(row["match_mz_error"]) <= params["mz_tolerance"],
                    abs(row["match_abundance_error"])
                    <= params["isotope_ratio_tolerance"],
                    max(row.get("match_isotope_correlation", 0), 0)
                    >= params["min_isotope_correlation"],
                    row["sample_peak_area"] >= params["peak_min_intensity"],
                    row["relative_abundance"] >= params["min_isotope_abundance"],
                ]
            )
            else 0
        )

        row["sample_peak_area"] = (
            row["sample_peak_area"]
            if all(
                [
                    abs(row["match_mz_error"]) <= params["mz_tolerance"],
                    abs(row["match_abundance_error"])
                    <= params["isotope_ratio_tolerance"],
                    max(row.get("match_isotope_correlation", 0), 0)
                    >= params["min_isotope_correlation"],
                    row["relative_abundance"] >= params["min_isotope_abundance"],
                ]
            )
            else 0
        )

        # Determine match category based on match_score
        match_score = row["match_score"]
        row["match_category"] = (
            2  # Probable match
            if match_score >= params["probable_match_threshold"]
            else (
                1  # Possible match
                if match_score >= params["possible_match_threshold"]
                else 0
            )  # No match
        )

        return row

    # Apply the filtering logic to each row
    filtered_df = match_isotope_df.apply(filter_row, axis=1)

    return filtered_df
