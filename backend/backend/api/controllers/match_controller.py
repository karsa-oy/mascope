"""
Match Controller

This module contains all the functionalities and endpoints related to the matching/rematching processes and related operations. 
"""

# -------------------------------------------------------------------
# Imports
# -------------------------------------------------------------------
import asyncio
import numpy as np
import pandas as pd
from fastapi import HTTPException
from typing import List, Optional
from sqlalchemy import select
from backend.db import async_session
from backend.api_sio import sio
from backend.db.id import gen_id
from lib.chemistry import match_mz
from lib.file_func import load_file
from lib.peak import detect_peaks, get_peaks
from lib.chemistry import match_mz
from lib.file_func import load_file
from lib.peak import detect_peaks, get_peaks
from ..utils.api_features import api_controller_background_task
from backend.api.models.models import (
    Sample,
    SampleBatch,
    SampleItem,
)
from ..exceptions import process_exception, ApiException
from .instrument_functions_controller import (
    read_instrument_functions,
)
from .samples_controller import get_sample, get_samples
from .matches_controller import get_matches, create_matches, delete_matches
from .helpers_controller import emit_progress_update
from .target_compounds_controller import get_target_compounds
from .target_isotopes_controller import (
    get_target_isotopes,
    get_target_isotopes_for_match_compute,
    get_target_isotopes_for_match_remove,
)
from .match_interferences_controller import (
    get_match_interferences,
    create_match_interferences,
    delete_match_interferences,
)
from ..models.pydantic_models.match_pydantic_model import (
    RematchBatchesBody,
    MatchComputeSample,
    ProgressProperties,
)


# -------------------------------------------------------------------
# Main Logic Functions
# -------------------------------------------------------------------


async def compute_matches(
    filename,
    target_isotopes_df,
    min_isotope_abundance=0.15,
):
    """
    Computes matches for specified target isotopes within a sample file.

    This function identifies the best matching peaks within the sample spectrum for each target isotope based on
    their m/z values. It computes match statistics such as match score, m/z error, and isotope correlation.

    Steps:
    1. Load peaks from the sample file and prepare the data for matching.
    2. Match each target isotope to the closest peak within a predefined m/z tolerance window.
    3. Compute match statistics such as isotope correlations, m/z errors, and match score.
    4. Return a DataFrame containing the match details for each target isotope.

    :param filename: Path to the sample file to be analyzed for matches.
    :type filename: str
    :param target_isotopes_df: DataFrame containing target isotopes with their m/z values and other properties.
    :type target_isotopes_df: pd.DataFrame
    :param min_isotope_abundance: Minimum relative abundance threshold for isotopes to be considered in matching.
    :type min_isotope_abundance: float, optional
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
        instrument_functions = await read_instrument_functions(filename)
        sample_file = await detect_peaks(
            filename, instrument_functions, u_list, if_exists="append"
        )
        peaks = get_peaks(sample_file, "area")

        # Step 2: - Prepare data
        # init match df from target isotopes
        match_isotope_df = target_isotopes_df.copy().assign(
            match_id=np.nan,
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
            match_indeces, match_mzs = match_mz(
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
                row["match_id"] = gen_id(length=32)
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
        match_isotope_df["match_isotope_correlation"].fillna(value=0, inplace=True)
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
        sample_file_data = load_file(filename, vars=["signal"])
        sum_spectrum = sample_file_data.signal.sum(dim="time").compute()

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


async def compute_sample_match(
    sample: MatchComputeSample,
    target_isotopes_df,
    progress_properties: ProgressProperties = None,
):
    """
    Computes matches and match interferences for a given sample against a set of target isotopes.

    This function takes a sample and a DataFrame containing target isotopes, computes match interferences, and matches for the sample.
    It updates the computation progress if progress properties are provided. Matches and interferences are then saved to the database.

    Steps:
    1. Unpack sample parameters including sample item ID and filename.
    2. Compute match interferences for the sample using the provided target isotopes.
    3. Compute matches for the sample using the provided target isotopes.
    4. Save computed match interferences and matches to the database, ensuring no duplication.
    5. Update computation progress at each significant step if progress tracking is enabled.

    :param sample: Contains details of the sample for which matches are being computed, including sample item ID and filename.
    :type sample: MatchComputeSample
    :param target_isotopes_df: A DataFrame containing target isotope information for match computation.
    :type target_isotopes_df: DataFrame
    :param progress_properties: Optional parameters for tracking progress of match computation.
    :type progress_properties: ProgressProperties, optional
    :raises RuntimeError: If no match interferences or matches are found during computation.
    """
    try:
        # Step 1: Unpack the sample parameters for ease of use
        sample_item_id = sample.sample_item_id
        filename = sample.filename

        #  Update progress if properties are provided (initial increment for setup/start).
        if progress_properties:
            await emit_progress_update(
                progress_properties=progress_properties, increment=0.25
            )

        # Step 2: Compute match interferences for the given sample and target isotopes.
        print("Computing match interferences for file: %s" % filename)
        match_interference_df = await compute_match_interferences(
            filename, target_isotopes_df
        )
        # Emit a progress update after computing interferences
        if progress_properties:
            await emit_progress_update(
                progress_properties=progress_properties, increment=0.5
            )

        # Step 3: Compute matches for the given sample and target isotopes.
        print("Computing matches for file: %s" % filename)
        match_isotope_df = await compute_matches(filename, target_isotopes_df)
        # Emit a progress update after computing matches
        if progress_properties:
            await emit_progress_update(
                progress_properties=progress_properties, increment=0.75
            )

        # Step 4: Save computed interferences and matches to the database
        # Check if any interferences were found and save them
        if not match_interference_df.empty:
            await create_match_interferences(match_interference_df, sample_item_id)
        else:
            raise RuntimeError("No match interferences found")

        # Check if any matches were found and save them
        if not match_isotope_df.empty:
            await create_matches(match_isotope_df, sample_item_id)
        else:
            raise RuntimeError("No matches found")

        # Emit a final progress update indicating completion
        if progress_properties:
            await emit_progress_update(
                progress_properties=progress_properties, increment=1
            )

    except Exception as e:
        error_message = f"Computing sample matches failed: {e}"
        raise RuntimeError(error_message)


async def filter_existing_sample_matches_and_interferences(
    target_isotopes_df, sample_item_id
):
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
        existing_matches = await get_matches(sample_item_id=sample_item_id)
        existing_interferences = await get_match_interferences(
            sample_item_id=sample_item_id
        )

        # Step 2: Compile sets of target isotope IDs from existing matches and interferences.
        existing_match_ids = {
            match["target_isotope_id"] for match in existing_matches["data"]
        }
        existing_interference_ids = {
            interference["target_isotope_id"]
            for interference in existing_interferences["data"]
        }

        # Step 3: Filter out isotopes from the DataFrame that already have matches or interferences.
        target_isotopes_df = target_isotopes_df[
            ~target_isotopes_df["target_isotope_id"].isin(
                existing_match_ids | existing_interference_ids
            )
        ]

        # Step 4: Return the filtered DataFrame, which now only contains isotopes without existing matches or interferences.
        return target_isotopes_df
    except Exception as e:
        error_message = f"Filtering existing matches and interferences failed: {e}"
        raise RuntimeError(error_message)


# -------------------------------------------------------------------
# Controller or Route Handlers
# -------------------------------------------------------------------


# -------------------------------------------------------------------
# Sample level
# -------------------------------------------------------------------
@api_controller_background_task(
    success_emit_events=[
        ("rematch_finished", "sample_batch_id"),
        ("sample_batch_reload", "sample_batch_id"),
    ],
    error_emit_events=[
        ("rematch_finished", "sid"),
    ],
    default_payload={
        "action": "rematch",
        "type": "sample",
    },
    success_message="Sample was successfully rematched",
)
async def rematch_sample(
    sample_item_id: str,
    added_target_compound_ids: Optional[List[str]] = None,
    added_ionization_mechanism_ids: Optional[List[str]] = None,
    removed_target_compound_ids: Optional[List[str]] = None,
    removed_ionization_mechanism_ids: Optional[List[str]] = None,
    independent_transaction: bool = False,
    sid: str = None,
) -> dict:
    """
    Performs a rematch of sample by removing and/or computing matches based on the specified parameters.

    This function handles the rematch process of a sample by first removing matches associated with removed
    target compounds or ionization mechanisms and then adding matches for added compounds or mechanisms.
    If no parameters are provided, it performs a complete rematch by removing all existing sample matches and recomputing them.

    Steps:
    1. Remove existing matches associated with removed parameters, if specified.
    2. Compute new matches for added parameters, if specified.
    3. In the absence of specified parameters for addition or removal, perform a full rematch by removing all matches and recomputing them for all targets of the sample.
    4. Return the rematched sample.
    5. Emit a finished and reload events to update the system with the changes, if the operation is flagged as an independent transaction.
        TODO_notifications handle the events + send the data to payload
        The event emission for 'rematch_finished' and 'sample_batch_reload' is handled by the api_controller_background_task decorator based on operation success or failure

    :param sample_item_id: ID of the sample item for which the rematch is to be performed.
    :type sample_item_id: str
    :param added_target_compound_ids: List of target compound IDs for which matches need to be computed, defaults to None
    :type added_target_compound_ids: Optional[List[str]], optional
    :param added_ionization_mechanism_ids: List of ionization mechanism IDs for which matches need to be computed, defaults to None
    :type added_ionization_mechanism_ids: Optional[List[str]], optional
    :param removed_target_compound_ids: List of target compound IDs for which matches are to be removed, defaults to None
    :type removed_target_compound_ids: Optional[List[str]], optional
    :param removed_ionization_mechanism_ids: List of ionization mechanism IDs for which matches are to be removed, defaults to None
    :type removed_ionization_mechanism_ids: Optional[List[str]], optional
    :param independent_transaction: Flag indicating whether the ramtching is an independent transaction, which affects event emission, defaults to False
    :type independent_transaction: bool, optional
    :param sid: Session ID, used for targeting specific clients when emitting events, defaults to None
    :type sid: str, optional
    :return: The dict with rematched Sample object.
    rtype: dict

    Notes:
        - If `removed_*` parameters are provided, the function removes matches related to these parameters.
        - If `added_*` parameters are provided, the function computes new matches related to these parameters.
        - If no `added_*` or `removed_*` parameters are provided, the function removes all existing matches and computes new matches for all targets.
    """
    print(f"...Rematching sample: {sample_item_id} ...")
    # Fetch sample data
    sample = await get_sample(sample_item_id)

    # Step 1: Remove existing matches based on provided removed parameters
    if removed_target_compound_ids or removed_ionization_mechanism_ids:
        await match_sample_remove(
            sample_item_id=sample_item_id,
            removed_target_compound_ids=removed_target_compound_ids,
            removed_ionization_mechanism_ids=removed_ionization_mechanism_ids,
        )

    # Step 2: Compute new matches based on provided added parameters
    if added_target_compound_ids or added_ionization_mechanism_ids:
        await match_sample_compute(
            sample_item_id=sample_item_id,
            added_target_compound_ids=added_target_compound_ids,
            added_ionization_mechanism_ids=added_ionization_mechanism_ids,
        )
    # Step 3: Perform a complete rematch if no specific targets are provided
    elif not removed_target_compound_ids and not removed_ionization_mechanism_ids:
        await match_sample_remove(
            sample_item_id=sample_item_id
        )  # Remove all existing matches
        await match_sample_compute(
            sample_item_id=sample_item_id
        )  # Compute matches for all targets

    # Step 4: Return rematched sample dict so that api_controller_background_task wrapper would have access to the sio room keys for success_emit_events
    return sample


async def match_sample_remove(
    sample_item_id: str,
    removed_target_compound_ids: Optional[List[str]] = None,
    removed_ionization_mechanism_ids: Optional[List[str]] = None,
    independent_transaction: bool = False,
):
    """
    Removes matches and match interferences for a specific sample item, potentially filtered by specific target compounds or ionization mechanisms.

    This function deletes matches (and associated match interferences) for a given sample item.
    When provided, filters based on removed target compounds or ionization mechanisms are applied, limiting the deletion to matches associated with those criteria.
    If no filters are specified, all matches for the sample item are removed. This operation can be performed as part of a larger transaction (rematch_sample endpoint)
    or as an independent transaction (Postman), in which case a reload event is emitted for the sample batch.

    Steps:
    1. Identify the sample item for match deletion.
    2. If specified, determine the target isotope IDs linked to the removed compounds or ionization mechanisms, which will limit the deletion of related matches.
    3. Execute the deletion of matches and associated interferences based on the identified target isotope IDs or remove all matches if no filters are applied.
    4. If operating as an independent transaction, emit a reload event for the sample batch to reflect the changes.

    :param sample_item_id: Unique identifier for the sample item whose matches are to be removed.
    :type sample_item_id: str
    :param removed_target_compound_ids: List of target compound IDs to filter the matches that need to be removed, optional.
    :type removed_target_compound_ids: Optional[List[str]]
    :param removed_ionization_mechanism_ids: List of ionization mechanism IDs to filter the matches that need to be removed, optional.
    :type removed_ionization_mechanism_ids: Optional[List[str]]
    :param independent_transaction: Flag indicating whether the operation should be treated as an independent transaction, defaults to False.
    :type independent_transaction: bool
    :raises HTTPException: Raises an HTTPException if the operation fails during an independent transaction.
    :raises RuntimeError: Raises a RuntimeError for internal call failures when not in an independent transaction.
    """
    try:
        print(f"...Removing matches for sample: {sample_item_id} ...")

        # Step 1: Identify the sample item for match deletion.
        sample_item_ids = [sample_item_id]
        target_isotope_ids = None

        # Step 2: Determine the target isotope IDs that are associated with the removed compounds or ionization mechanisms.
        target_isotope_ids = None
        if removed_target_compound_ids or removed_ionization_mechanism_ids:
            (
                target_isotope_ids,
                applied_filters,
            ) = await get_target_isotopes_for_match_remove(
                removed_target_compound_ids,
                removed_ionization_mechanism_ids,
            )
            print(f"Removing matches associated with {applied_filters}")
        else:
            print(f"Removing all matches and match interferences")

        # Step 3: Delete matches and match interferences corresponding to these isotopes.
        await delete_matches(sample_item_ids, target_isotope_ids)
        await delete_match_interferences(sample_item_ids, target_isotope_ids)

        # Step 4: Emit a reload event for the sample batch if this is an independent transaction.
        # Reload affected sample batch if called by http request
        if independent_transaction:
            async with async_session() as session:
                result = await session.execute(
                    select(SampleItem.sample_batch_id).where(
                        SampleItem.sample_item_id == sample_item_id
                    )
                )
                sample_batch_id = result.scalar_one_or_none()
                if sample_batch_id:
                    await sio.emit(
                        "sample_batch_reload", room=sample_batch_id, namespace="/"
                    )
    except Exception as e:
        error_message = f"Removing sample item matches failed: {e}"
        print(error_message)
        if independent_transaction:
            raise HTTPException(status_code=400, detail=error_message)
        else:
            # Exception for internal calls (from rematch_sample)
            raise RuntimeError(error_message)


@api_controller_background_task(
    # success_emit_events=[
    #     ("match_compute_finished", "sample_batch_id"),
    #     ("sample_batch_reload", "sample_batch_id"),
    # ],
    # error_emit_events=[
    #     ("match_compute_finished", "sid"),
    # ],
    # default_payload={
    #     "action": "match_compute",
    #     "type": "sample",
    # },
    # success_message="Sample matches were successfully computed",
    # TODO_notifications refactor the events + send the data to payload when success as a result["sio_payload"] (?) if success, in the exception
    # we should (?) emit the error event to sid, since it is accessible from the wrapper kwargs
)
async def match_sample_compute(
    sample_item_id: str,
    added_target_compound_ids: Optional[List[str]] = None,
    added_ionization_mechanism_ids: Optional[List[str]] = None,
    independent_transaction: bool = False,
    sid: str = None,
):
    """
    Computes new matches for a specific sample item, taking into account any added target compounds or ionization mechanisms.

    This function handles the computation of matches for a given sample item.
    It accommodates the inclusion of added target compounds or ionization mechanisms by determining the relevant target isotopes that require match computation.
    It ensures that redundant computations are avoided by checking for pre-existing matches and match interferences.

    Steps:
    1. Gather necessary sample information.
    2. Retrieve associated batch information and its ionization mechanisms.
    3. Determine target isotopes that require new match computation.
    4. Check if there are existing match records for these target isotopes to avoid redundancy.
    5. Proceed with match computation if there are target isotopes to process.
    6. Emit reload event for the affected batch users if this function is called as an independent transaction.

    :param sample_item_id: ID of the sample item for which matches are to be computed.
    :type sample_item_id: str
    :param added_target_compound_ids: List of added target compound IDs to be considered for match computation, defaults to None
    :type added_target_compound_ids: Optional[List[str]], optional
    :param added_ionization_mechanism_ids: List of added ionization mechanism IDs to be considered for match computation, defaults to None
    :type added_ionization_mechanism_ids: Optional[List[str]], optional
    :param independent_transaction: Flag indicating whether the sample match computing is an independent transaction, which affects event emission, defaults to False
    :type independent_transaction: bool, optional
    :param sid: Session ID, used for targeting specific clients when emitting events, defaults to None
    :type sid: str, optional
    :raises RuntimeError: Raised when no new target isotopes are available for match computation.
    :return: The dict with rematched Sample object.
    rtype: dict

    TODO: - optimize instrument/compute_sample_match notifications emits/listeners. item compute for instrument users (Scenthound)
          - sid can be passed to send the notifications for user who triggered computing (for example when copy the sample item)
    """
    try:
        # Step 1: Gather sample information

        # Fetch sample data
        sample = await get_sample(sample_item_id)

        # Extract sample required fields
        sample_item_name = sample["sample_item_name"]
        sample_batch_id = sample["sample_batch_id"]
        filename = sample["filename"]
        instrument = sample["instrument"]

        # Check if 'verified' exists in mz_calibration. If not, provide a default value of False
        verified = (
            sample["mz_calibration"].get("verified", False)
            if sample["mz_calibration"] is not None
            else True
        )

        # Prepare data for match computation
        sample_pydantic = MatchComputeSample(
            sample_item_id=sample_item_id,
            sample_item_name=sample_item_name,
            sample_batch_id=sample_batch_id,
            filename=filename,
            instrument=instrument,
        )

        # Prepare progress_properties for correct notifications.
        progress_properties = ProgressProperties(
            progress_type="match_item",
            sample_batch_id=sample_batch_id,
        )

        # Step 2: Gather batch information

        # Fetch ionization mechanisms from the batch
        async with async_session() as session:
            result = await session.execute(
                select(SampleBatch)
                .join(Sample)
                .where(Sample.sample_item_id == sample_item_id)
            )
            sample_batch = result.scalars().first()

        build_params = sample_batch.build_params
        batch_ion_mechanisms_ids = build_params["ion_mechanisms"]

        # Fetch target compounds of the batch
        batch_target_compounds_result = await get_target_compounds(
            sample_batch_id=sample_batch.sample_batch_id,
        )
        batch_target_compounds_ids = [
            compound["target_compound_id"]
            for compound in batch_target_compounds_result["data"]
        ]

        # Step 3: Get the target isotopes for which match computing is needed.
        # If compounds/ion_mechanisms were added get isotopes with specific filters.
        # If no compounds/ion_mechanisms were added get all target isotopes for the sample's batch.

        # Compute new matches for added compounds and mechanisms
        target_isotopes_df = None

        if added_target_compound_ids or added_ionization_mechanism_ids:
            # Get necessary target isotopes for computing new matches of added compounds/ion_mechanisms
            (
                target_isotopes,
                applied_filters,
            ) = await get_target_isotopes_for_match_compute(
                batch_target_compounds_ids,
                batch_ion_mechanisms_ids,
                added_target_compound_ids,
                added_ionization_mechanism_ids,
            )
            print(f"Match computing is specifed for the list of {applied_filters}")
            target_isotopes_df = pd.DataFrame(target_isotopes)
        else:
            # Fetch all target isotopes for the sample's batch
            target_isotopes_result = await get_target_isotopes(
                sample_batch_id=sample_batch_id,
            )
            target_isotopes_df = pd.DataFrame(target_isotopes_result["data"])
            print(
                f"Computing matches and match interferences for all sample target isotopes. Total isotopes: {len(target_isotopes_df)}"
            )

        # Check if there are already records in matches and match interferences for the target isotopes.
        target_isotopes_df = await filter_existing_sample_matches_and_interferences(
            target_isotopes_df, sample_item_id
        )

        # Step 4: Process sample for match computation.
        print(
            f"...Computing matches for sample {sample_item_name}: {sample_item_id} ..."
        )

        # notification for the batch users
        await sio.emit(
            "match_item_update_compute_started",
            {
                "sample_item_name": sample_item_name,
            },
            room=sample_batch_id,
            namespace="/",
        )

        # notification for the instrument users
        await sio.emit(
            "match_item_compute_started",
            {
                "filename": filename,
                "progress": 0,
            },
            room=instrument,
            namespace="/",
        )
        await sio.emit(
            "match_item_compute_progress", {}, room=instrument, namespace="/"
        )

        # Skip computation if no new target isotopes are found for this sample item
        if target_isotopes_df.empty or target_isotopes_df is None:
            error_message = f"No new target isotopes to compute matches for."
            raise ValueError(error_message)

        # Check if m/z calibration is verified for the sample
        if not verified:
            error_message = f"m/z calibration is not verified for sample file: {filename}. Please try to calibrate the file."
            raise ValueError(error_message)

        # Step 5: Compute matches for the sample if passed all checks,

        await compute_sample_match(
            sample_pydantic, target_isotopes_df, progress_properties
        )

        # notification for the batch users
        await sio.emit(
            "match_item_update_compute_finished",
            {
                "sample_item_name": sample_item_name,
            },
            room=sample_batch_id,
            namespace="/",
        )

        # notification for the instrument users
        await sio.emit(
            "match_item_compute_finished",
            {
                "filename": filename,
                "progress": 100,
            },
            room=instrument,
            namespace="/",
        )

        # Step 6: Emit reload event for the batch users if this function is called as an independent transaction.
        if independent_transaction:
            await sio.emit("sample_batch_reload", room=sample_batch_id, namespace="/")
    except Exception as e:
        print(f"Computing sample item matches failed: {e}")

        # notification for the instrument users
        await sio.emit(
            "match_item_compute_failed",
            {
                "filename": filename,
                "progress": 100,
            },
            room=instrument,
            namespace="/",
        )

        # notification for the batch users
        await sio.emit(
            "match_item_update_compute_failed",
            {
                "sample_item_name": sample_item_name,
                "errorMessage": str(e),
            },
            room=sample_batch_id,
            namespace="/",
        )
        if independent_transaction:
            await sio.emit("sample_batch_reload", room=sample_batch_id, namespace="/")


# -------------------------------------------------------------------
# Batch level
# -------------------------------------------------------------------


@api_controller_background_task(
    # TODO_notifications implement the success/error notifications as example below
    error_emit_events=[
        ("rematch_finished", "sid"),
    ],
    default_payload={
        "action": "rematch",
        "type": "batch",
    },
)
async def rematch_batches(
    rematch_batches_body: RematchBatchesBody,
    independent_transaction: bool,
    sid: str,
) -> dict:
    """
    Performs a rematch operation on multiple sample batches based on the provided for each batch batch-specific
    removed- or added- parameters in target compounds or ionization mechanisms.

    This function iterates over each sample batch, creating separate rematch_batch task with
    removed- or added- parameters in target compounds or ionization mechanisms for each batch.
    It also aggregates any failures across batches for reporting purposes.

    Steps:
    1. Gather initial data for each sample batch, including the number of items per batch and workspace IDs.
    2. Notify client who triggered rematch_batches that batches processing has started.
    3. Sequentially process each sample batch with the specific for each batch added and removed parameters.
    4. Aggregate failed samples from each batch for reporting.
    5. Notify client who triggered rematch_batches that batches processing has finished, including information about any failures.


    :param rematch_batches_body: A list of sample batch identifiers along with optional removed/added entities
    :type rematch_batches_body: RematchBatchesBody
    :param independent_transaction: Flag to indicate if the operation should be treated as an independent transaction
    :type independent_transaction: bool
    :param sid: Session ID, used for emitting notifications to specific clients
    :type sid: str
    :return: A status message indicating the outcome of the batch rematch operation, including any failed match computations for samples.
    :rtype: dict

    TODO_notifications
        - Refactor notifications
        - return data and add this as "data" to sio notification success payload in the api_controller_background_task
    """
    # Initialize variables for tracking overall progress and failures for correct user notifications
    total_batches = len(rematch_batches_body.sample_batches)
    total_number_of_items = 0
    items_per_batch = []
    samples_compute_failed_all = []  # to collect failed samples from all batches

    # Step 1: Gather data for each batch and set workspace_id for each batch
    for sample_batch in rematch_batches_body.sample_batches:
        sample_items_info = await get_samples(
            sample_batch_id=sample_batch.sample_batch_id, batch_matches_info=False
        )
        total_number_of_items += sample_items_info["results"]
        items_per_batch.append(sample_items_info["results"])

        # Fetch workspace_id from the database
        async with async_session() as session:
            result = await session.execute(
                select(SampleBatch.workspace_id).filter(
                    SampleBatch.sample_batch_id == sample_batch.sample_batch_id
                )
            )
            sample_batch.workspace_id = result.scalar_one_or_none()

    # Calculate weight for each batch based on the number of items
    item_weights_per_batch = [1.0 / items if items else 0 for items in items_per_batch]

    # Step 2: Notify client who triggered rematch_batches that batches processing has started.
    await sio.emit(
        "rematch_batches_started",
        {"total_batches": total_batches},
        room=sid,
        namespace="/",
    )

    # Step 3: Process each batch
    for batch_index, sample_batch in enumerate(
        rematch_batches_body.sample_batches, start=1
    ):
        sample_batch_id = sample_batch.sample_batch_id
        workspace_id = sample_batch.workspace_id
        added_target_compound_ids = sample_batch.added_target_compound_ids
        removed_target_compound_ids = sample_batch.removed_target_compound_ids

        # Notify workspace client of the current progres batch
        await sio.emit(
            "rematch_batch_progress",
            {"current_batch": batch_index},
            room=sid,
            namespace="/",
        )

        # Compute progress properties for the current batch
        progress_properties = ProgressProperties(
            progress_type="rematch_batches",
            sample_batch_id=sample_batch_id,
            item_weight=item_weights_per_batch[batch_index - 1],
            batch_index=batch_index,
            workspace_id=workspace_id,
            total_batches=total_batches,
            sid=sid,
        )

        # Create rematching task for the current batch
        task = asyncio.create_task(
            rematch_batch(
                sample_batch_id=sample_batch_id,
                workspace_id=workspace_id,
                added_target_compound_ids=added_target_compound_ids,
                removed_target_compound_ids=removed_target_compound_ids,
                independent_transaction=False,
                progress_properties=progress_properties,
            )
        )

        # Perform the rematch operation for the current batch
        task_result = await task

        # Step 4: Aggregate failed samples from the batch for reporting
        # If the task result contains information about failed samples, aggregate this information for all batches
        if task_result and "samples_compute_failed" in task_result:
            samples_compute_failed_all.extend(task_result["samples_compute_failed"])

    # Step 5: Notify client who triggered rematching that batches processing has finished, including information about any failures
    await sio.emit(
        "rematch_batches_finished",
        {
            "total_batches": total_batches,
            "samples_compute_failed": samples_compute_failed_all,
        },
        room=sid,
        namespace="/",
    )

    if samples_compute_failed_all:
        # If there are any aggregated failed samples from all batches, include this information in the final result
        return {
            "status": f"Match computation for {total_batches} batches. Failed samples: {samples_compute_failed_all}"
        }
    else:
        return {"status": f"Match computation for {total_batches} batches"}


async def rematch_batch(
    sample_batch_id: str,
    workspace_id: Optional[str] = None,
    added_target_compound_ids: Optional[List[str]] = None,
    added_ionization_mechanism_ids: Optional[List[str]] = None,
    removed_target_compound_ids: Optional[List[str]] = None,
    removed_ionization_mechanism_ids: Optional[List[str]] = None,
    independent_transaction: bool = False,
    progress_properties: ProgressProperties = None,
):
    """
    Performs a rematch of sample batch by removing and/or computing matches based on the specified parameters.
    This operation can be conducted as part of a larger rematch_batches operation or as an independent transaction.

    This function handles the rematch process of a sample batch by first removing matches associated with removed
    target compounds or ionization mechanisms and then adding matches for added compounds or mechanisms.
    If no parameters are provided, it performs a complete rematch by removing all existing sample matches and recomputing them.

    Steps:
    1. Notify batch clients that batch processing has started.
    2. Remove existing matches associated with removed parameters, if specified.
    3. Compute new matches for added parameters, if specified.
    4. In the absence of specified parameters for addition or removal, perform a full rematch by removing all matches and recomputing them for all targets of the batch.
    5. Emit a reload event for the batch users to update the system with the changes, if the operation is flagged as an independent transaction.
    6. Notify batch clients that  batch rematching has finished, including information about any failures
    7. If there are any failed samples, return them as part of the function's result to be processed in rematch_batches endpoint

    :param sample_batch_id: ID of the sample batch for which the rematch is to be performed.
    :type sample_batch_id: str
    :param added_target_compound_ids: List of target compound IDs for which matches need to be computed, defaults to None
    :type added_target_compound_ids: Optional[List[str]], optional
    :param added_ionization_mechanism_ids: List of ionization mechanism IDs for which matches need to be computed, defaults to None
    :type added_ionization_mechanism_ids: Optional[List[str]], optional
    :param removed_target_compound_ids: List of target compound IDs for which matches are to be removed, defaults to None
    :type removed_target_compound_ids: Optional[List[str]], optional
    :param removed_ionization_mechanism_ids: List of ionization mechanism IDs for which matches are to be removed, defaults to None
    :type removed_ionization_mechanism_ids: Optional[List[str]], optional

    Notes:
        - If `removed_*` parameters are provided, the function removes matches related to these parameters.
        - If `added_*` parameters are provided, the function computes new matches related to these parameters.
        - If no `added_*` or `removed_*` parameters are provided, the function removes all existing matches and computes new matches for all targets.
    TODO_notifications
        - Handle the separate types of notifications when called from rematch_batches or when an independent transaction, potentially using sid
    """
    print(f"...Rematching batch: {sample_batch_id} ...")
    samples_compute_failed = []
    try:
        # Step 1: Notify batch clients that batch processing has started.
        await sio.emit(
            "rematch_batch_started",
            {"total_batches": 1},
            room=sample_batch_id,
            namespace="/",
        )
        if progress_properties.progress_type == "rematch_batch":
            # Compute progress properties for the current batch
            sample_items_info = await get_samples(
                sample_batch_id=sample_batch_id,
                batch_matches_info=False,
            )
            item_weight = 1.0 / sample_items_info["results"]
            if progress_properties.workspace_reload is not None:
                workspace_reload = progress_properties.workspace_reload
            else:
                workspace_reload = False

            progress_properties = ProgressProperties(
                progress_type=progress_properties.progress_type,
                item_weight=item_weight,
                batch_index=1,
                total_batches=1,
                workspace_reload=workspace_reload,
                sample_batch_id=sample_batch_id,
            )
            if not workspace_id:
                # Fetch workspace_id from the database
                async with async_session() as session:
                    result = await session.execute(
                        select(SampleBatch.workspace_id).filter(
                            SampleBatch.sample_batch_id == sample_batch_id
                        )
                    )
                    workspace_id = result.scalar_one_or_none()

            # Notify batch clients of the progres
            await sio.emit(
                "rematch_batch_progress",
                {"current_batch": progress_properties.batch_index},
                room=sample_batch_id,
                namespace="/",
            )
        # Notify sample batch clients of the selected batch processing
        await sio.emit(
            "rematch_batch_progress",
            {
                "current_batch_message": "Selected batch is processing now",
            },
            room=sample_batch_id,
            namespace="/",
        )

        # Step 2: Remove existing matches based on provided removed parameters
        if removed_target_compound_ids or removed_ionization_mechanism_ids:
            await match_batch_remove(
                sample_batch_id=sample_batch_id,
                removed_target_compound_ids=removed_target_compound_ids,
                removed_ionization_mechanism_ids=removed_ionization_mechanism_ids,
            )

        # Step 3: Compute new matches based on provided added parameters
        if added_target_compound_ids or added_ionization_mechanism_ids:
            await match_batch_compute(
                sample_batch_id=sample_batch_id,
                added_target_compound_ids=added_target_compound_ids,
                added_ionization_mechanism_ids=added_ionization_mechanism_ids,
                progress_properties=progress_properties,
            )
        # Step 4: Perform a complete rematch if no specific targets are provided
        elif not removed_target_compound_ids and not removed_ionization_mechanism_ids:
            await match_batch_remove(
                sample_batch_id=sample_batch_id,
            )  # Remove all existing matches
            await match_batch_compute(
                sample_batch_id=sample_batch_id, progress_properties=progress_properties
            )  # Compute matches for all targets

    except Exception as e:
        # Extract error information from the exception, specifically looking for "failed_samples"
        context_message = f"Failed to rematch sample batch '{sample_batch_id}'"
        api_exc = process_exception(e, context_message)
        user_error_message = api_exc.user_message
        detail = api_exc.tech_message

        # reise the error if called internally, from import_sample_items
        if independent_transaction:
            print(user_error_message)
            print(detail)
        else:
            raise ApiException(user_error_message, detail, api_exc.status_code)

        error_info = e.args[0]
        # If the exception contains information about failed samples, extend the failed samples list with this information
        if "failed_samples" in error_info:
            samples_compute_failed = error_info["failed_samples"]
        else:
            # If no specific failed samples information is present, log the general error
            print("Error:", error_info)

    # Step 5: Emit a reload event if this operation is independent
    if progress_properties.workspace_reload:
        await sio.emit("workspace_reload", room=workspace_id, namespace="/")
    else:
        await sio.emit("sample_batch_reload", room=sample_batch_id, namespace="/")

    # Step 6: Notify batch clients that  batch rematching has finished, including information about any failures
    await sio.emit(
        "rematch_batch_finished",
        {
            "total_batches": 1,
            "samples_compute_failed": samples_compute_failed,
        },
        room=sample_batch_id,
        namespace="/",
    )

    # Step 7: If there are any failed samples, return them as part of the function's result to be processed in rematch_batches endpoint
    if samples_compute_failed:
        return {"samples_compute_failed": samples_compute_failed}

    return None


async def match_batch_remove(
    sample_batch_id: str,
    removed_target_compound_ids: Optional[List[str]] = None,
    removed_ionization_mechanism_ids: Optional[List[str]] = None,
    independent_transaction: bool = False,
):
    """
    Removes matches associated with a sample batch, optionally filtering by removed target compounds or ionization mechanisms.

    This function deletes matches (and associated match interferences) for a given sample batch. If removed target compound IDs or ionization
    mechanism IDs are provided, the function fetches associated target isotope IDs and deletes matches specific to these isotopes.
    If no filters are provided, all matches for the batch are deleted.

    Steps:
    1. Retrieve all sample items associated with the sample batch.
    2. Determine the target isotope IDs that are associated with the removed compounds or ionization mechanisms.
    3. Execute the deletion of matches and associated interferences based on the identified target isotope IDs or remove all matches if no filters are applied.
    4. Emit a reload event for the sample batch if this is an independent transaction.

    :param sample_batch_id: ID of the sample batch for which matches are to be removed.
    :type sample_batch_id: str
    :param removed_target_compound_ids: List of target compound IDs for which matches are to be removed, optional.
    :type removed_target_compound_ids: Optional[List[str]]
    :param removed_ionization_mechanism_ids: List of ionization mechanism IDs for which matches are to be removed, optional.
    :type removed_ionization_mechanism_ids: Optional[List[str]]
    :param independent_transaction: Flag indicating if the operation should be an independent transaction, default to False.
    :type independent_transaction: bool
    """
    try:
        print(f"...Removing matches for batch: {sample_batch_id} ...")

        # Step 1: Retrieve all sample items associated with the sample batch.
        sample_items_data = await get_samples(
            sample_batch_id=sample_batch_id, batch_matches_info=False
        )
        sample_item_ids = [
            sample_item["sample_item_id"] for sample_item in sample_items_data["data"]
        ]

        # Step 2: Determine the target isotope IDs that are associated with the removed compounds or ionization mechanisms.
        target_isotope_ids = None
        if removed_target_compound_ids or removed_ionization_mechanism_ids:
            (
                target_isotope_ids,
                applied_filters,
            ) = await get_target_isotopes_for_match_remove(
                removed_target_compound_ids,
                removed_ionization_mechanism_ids,
            )
            print(f"Removing matches associated with {applied_filters}")
        else:
            print(f"Removing all matches and match interferences")

        # Step 3: Delete matches and match interferences corresponding to these isotopes.
        await delete_matches(sample_item_ids, target_isotope_ids)
        await delete_match_interferences(sample_item_ids, target_isotope_ids)

        # Step 4: Emit a reload event for the sample batch if this is an independent transaction.
        # Reload affected sample batch if called by http request
        if independent_transaction:
            await sio.emit("sample_batch_reload", room=sample_batch_id, namespace="/")
    except Exception as e:
        error_message = f"Removing batch matches failed: {e}"
        print(error_message)
        if independent_transaction:
            raise HTTPException(status_code=400, detail=error_message)
        else:
            # Exception for internal calls (from rematch_batch)
            raise RuntimeError(error_message)


async def match_batch_compute(
    sample_batch_id: str,
    added_target_compound_ids: Optional[List[str]] = None,
    added_ionization_mechanism_ids: Optional[List[str]] = None,
    independent_transaction: bool = False,
    progress_properties: ProgressProperties = None,
):
    """
    Computes new matches for all samples within a given batch, taking into account any added target compounds or ionization mechanisms.

    This function handles the computation of matches for each sample item in the specified sample batch.
    It accommodates the inclusion of added target compounds or ionization mechanisms by determining the relevant target isotopes that require match computation.
    It ensures that redundant computations are avoided by checking for pre-existing matches and match interferences.

    Steps:
    1. Retrieve all samples associated with the given sample batch.
    2. Gather batch-specific information, including ionization mechanisms and target compounds.
    3. Determine target isotopes for which new match computation is required (specific to added compounds/ion_mechanisms or for all the batch targets in case of complete rematching).
    4. For each sample in the batch, preprocess sample data and check for existing matches.
    5. Compute matches for the sample items where new target isotopes are identified.
    6. Emit reload event for the batch if this function is called as an independent transaction.
    7. If there are any failed samples, raise an exception with the list of failed samples included in the error message

    :param sample_batch_id: The identifier of the sample batch for which match computation is to be performed.
    :type sample_batch_id: str
    :param added_target_compound_ids: A list of identifiers for target compounds that have been added to the batch, limiting the scope of match computation.
    :type added_target_compound_ids: Optional[List[str]], optional
    :param added_ionization_mechanism_ids: A list of identifiers for ionization mechanisms that have been added to the batch, limiting the scope of match computation.
    :type added_ionization_mechanism_ids: Optional[List[str]], optional
    :param independent_transaction: Indicates whether the match computation operation should be treated as a standalone process, which affects event emission and UI updates.
    :type independent_transaction: bool, optional
    :param progress_properties: Properties related to the progress tracking of the match computation process, facilitating user feedback.
    :type progress_properties: ProgressProperties, optional
    :raises ValueError: Raised in cases where match computation cannot proceed due to issues such as unverified m/z calibration or the absence new target isotopes to compute matches for.
    """
    print(f"...Computing matches of batch: {sample_batch_id} ...")

    # Step 1: Retrieve all samples associated with the specified sample batch.

    async with async_session() as session:
        # Fetch samples
        result = await session.execute(
            select(Sample).where(Sample.sample_batch_id == sample_batch_id)
        )

        samples = result.scalars().all()

    # Step 2: Gather batch information

    # Fetch ionization mechanisms from the batch
    async with async_session() as session:
        result = await session.execute(
            select(SampleBatch).where(SampleBatch.sample_batch_id == sample_batch_id)
        )
        sample_batch = result.scalars().first()

    build_params = sample_batch.build_params
    batch_ion_mechanisms_ids = build_params["ion_mechanisms"]

    # Fetch target compounds of the batch
    batch_target_compounds_result = await get_target_compounds(
        sample_batch_id=sample_batch.sample_batch_id,
    )
    batch_target_compounds_ids = [
        compound["target_compound_id"]
        for compound in batch_target_compounds_result["data"]
    ]

    # Step 3: Identify target isotopes for computation.
    #   If compounds/ion_mechanisms were added get isotopes with specific filters.
    #   If no compounds/ion_mechanisms were added get all target isotopes for the sample's batch.

    # Compute new matches for added compounds and mechanisms
    target_isotopes_df = None

    if added_target_compound_ids or added_ionization_mechanism_ids:
        # Get necessary target isotopes for computing new matches of added compounds/ion_mechanisms
        target_isotopes, applied_filters = await get_target_isotopes_for_match_compute(
            batch_target_compounds_ids,
            batch_ion_mechanisms_ids,
            added_target_compound_ids,
            added_ionization_mechanism_ids,
        )
        print(f"Match computing is specifed for the list of {applied_filters}")
        target_isotopes_df = pd.DataFrame(target_isotopes)
    else:
        # Fetch all target isotopes for the sample's batch
        target_isotopes_result = await get_target_isotopes(
            sample_batch_id=sample_batch_id,
        )
        target_isotopes_df = pd.DataFrame(target_isotopes_result["data"])
        print(
            f"Computing matches and match interferences for all batch target isotopes. Total isotopes: {len(target_isotopes_df)}"
        )

    # Step 4: Process each sample item for match computation.
    samples_compute_failed = []
    for item_index, sample in enumerate(samples):
        # Prepare data for match computation
        sample_pydantic = MatchComputeSample(
            sample_item_id=sample.sample_item_id,
            sample_item_name=sample.sample_item_name,
            sample_batch_id=sample.sample_batch_id,
            filename=sample.filename,
            instrument=sample.instrument,
        )
        # Prepare progress_properties for correct notifications.
        if progress_properties is not None:
            # Convert to dict and update 'item_index'
            progress_properties_dict = progress_properties.dict()
            progress_properties_dict["item_index"] = item_index

            progress_properties = ProgressProperties(**progress_properties_dict)

        try:
            # Gather sample information
            # Check if 'verified' exists in mz_calibration. If not, provide a default value of False
            verified = (
                sample.mz_calibration.get("verified", False)
                if sample.mz_calibration is not None
                else True
            )

            # Check if m/z calibration is verified for the sample
            if not verified:
                error_message = f"m/z calibration is not verified for sample file: {sample.filename}. Please try to calibrate the file."
                raise ValueError(error_message)

            # Filter existing matches and match interferences for the target isotopes fot each sample item.
            filtered_target_isotopes_df = (
                await filter_existing_sample_matches_and_interferences(
                    target_isotopes_df, sample.sample_item_id
                )
            )

            # Skip computation if no new target isotopes are found for this sample item
            if filtered_target_isotopes_df.empty:
                error_message = f"No new target isotopes to compute matches for."
                raise ValueError(error_message)

            # Step 5: Compute matches for the sample items that passed all checks,
            # where new target isotopes are identified, m/z calibration is verified.

            print(
                f"...Computing matches of sample item '{sample_pydantic.sample_item_name}' ..."
            )
            await compute_sample_match(
                sample_pydantic, filtered_target_isotopes_df, progress_properties
            )
        except Exception as e:
            # If an exception occurs during sample match computation, log the error and add the sample to the failed list
            print(f"Processing sample '{sample.sample_item_name}' failed: {e}")
            samples_compute_failed.append(
                {
                    "sample_item": {
                        "sample_item_id": sample_pydantic.sample_item_id,
                        "sample_item_name": sample_pydantic.sample_item_name,
                        "filename": sample_pydantic.filename,
                    },
                    "error_message": str(e),
                }
            )

    # Step 6: Emit reload event for the batch if this function is called as an independent transaction.
    if independent_transaction:
        await sio.emit("sample_batch_reload", room=sample_batch_id, namespace="/")

    # Step 7: If there are any failed samples, raise an exception with the list of failed samples included in the error message
    if samples_compute_failed:
        error_message = f"{len(samples_compute_failed)} samples failed to compute."
        raise ValueError(
            {"message": error_message, "failed_samples": samples_compute_failed}
        )
