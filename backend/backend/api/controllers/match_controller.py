"""
Match Controller

This module contains all the functionalities and endpoints related to the matching/rematching processes and related operations. 
"""

# -------------------------------------------------------------------
# Imports
# -------------------------------------------------------------------
import asyncio
from typing import List, Optional
import pandas as pd
from sqlalchemy import select
from backend.db import async_session
from backend.db.id import gen_id
from ..utils.api_features import (
    api_controller,
    api_controller_background_task,
    send_progress_user_notification,
)
from ..exceptions import ApiException, NotFoundException
from .samples_controller import get_sample, get_samples
from .target_compounds_controller import get_target_compounds
from .target_isotopes_controller import (
    get_target_isotopes,
    get_target_isotopes_for_match_compute,
    get_target_isotopes_for_match_remove,
)
from .matches_controller import (
    compute_matches,
    get_matches,
    create_matches,
    delete_matches,
)
from .match_interferences_controller import (
    compute_match_interferences,
    get_match_interferences,
    create_match_interferences,
    delete_match_interferences,
)
from ..models.models import (
    Sample,
    SampleBatch,
)
from ..models.pydantic_models.match_pydantic_model import (
    RematchBatchesBody,
    MatchComputeSample,
)
from ..models.pydantic_models.user_notification_pydantic_model import (
    UserNotification,
)

# TODO_configuration
# Default Filter Parameters
DEFAULT_MIN_ISOTOPE_ABUNDANCE = 0.15

# -------------------------------------------------------------------
# Main Logic Functions
# -------------------------------------------------------------------


@api_controller()
async def compute_sample_match(
    sample: MatchComputeSample,
    target_isotopes_df,
    notification: UserNotification = None,
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
    :param notification: Optional notification for sending progress user notifications of match computation.
    :type notification: UserNotification, optional
    :raises RuntimeError: If no match interferences or matches are found during computation.
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
    # Send progress user notificaton after computing interferences
    if notification:
        await send_progress_user_notification(notification, 0.5)

    # Step 3: Compute matches for the given sample and target isotopes.
    print("Computing matches for file: %s" % filename)
    match_isotope_df = await compute_matches(
        filename=filename,
        target_isotopes_df=target_isotopes_df,
        min_isotope_abundance=DEFAULT_MIN_ISOTOPE_ABUNDANCE,
    )
    # Send progress user notificaton after computing matches
    if notification:
        await send_progress_user_notification(notification, 0.75)

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

    # Send progress user notificaton indicating completion of compute_sample_match process
    if notification:
        await send_progress_user_notification(notification, 0.95)


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
    success_notification_rooms=["sample_batch_id"],
    success_reload=[("sample_batch_reload", "sample_batch_id")],
    error_notification_rooms=["sid"],
)
async def rematch_sample(
    sample_item_id: str,
    added_target_compound_ids: Optional[List[str]] = None,
    added_ionization_mechanism_ids: Optional[List[str]] = None,
    removed_target_compound_ids: Optional[List[str]] = None,
    removed_ionization_mechanism_ids: Optional[List[str]] = None,
    independent_transaction: bool = False,
    sid: str = None,
    process_id=None,
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
        The event emission for 'user_notification' and 'sample_batch_reload' is handled by the api_controller_background_task decorator based on operation success or failure

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
    # Step 1: Remove existing matches based on provided removed parameters
    if removed_target_compound_ids or removed_ionization_mechanism_ids:
        await match_sample_remove(
            sample_item_id=sample_item_id,
            removed_target_compound_ids=removed_target_compound_ids,
            removed_ionization_mechanism_ids=removed_ionization_mechanism_ids,
            independent_transaction=False,
            sid=sid,
            process_id=gen_id(8),
            parent_id=process_id,
        )

    # Step 2: Compute new matches based on provided added parameters
    if added_target_compound_ids or added_ionization_mechanism_ids:
        await match_sample_compute(
            sample_item_id=sample_item_id,
            added_target_compound_ids=added_target_compound_ids,
            added_ionization_mechanism_ids=added_ionization_mechanism_ids,
            independent_transaction=False,
            sid=sid,
            process_id=gen_id(8),
            parent_id=process_id,
        )
    # Step 3: Perform a complete rematch if no specific targets are provided
    elif not removed_target_compound_ids and not removed_ionization_mechanism_ids:
        await match_sample_remove(
            sample_item_id=sample_item_id,
            independent_transaction=False,
            sid=sid,
            process_id=gen_id(8),
            parent_id=process_id,
        )  # Remove all existing matches
        await match_sample_compute(
            sample_item_id=sample_item_id,
            independent_transaction=False,
            sid=sid,
            process_id=gen_id(8),
            parent_id=process_id,
        )  # Compute matches for all targets

    # Step 4: Return rematched sample and message
    sample = await get_sample(sample_item_id)
    sample_item_name = sample["sample_item_name"]
    return {
        "data": sample,
        "message": f"Sample '{sample_item_name}' was rematched.",
        "_notification_data": {
            "sample_item_id": sample_item_id,
        },
    }


@api_controller_background_task(
    success_notification_rooms=["sample_batch_id"],
    success_reload=[("sample_batch_reload", "sample_batch_id")],
    error_notification_rooms=["sid"],
)
async def match_sample_remove(
    sample_item_id: str,
    removed_target_compound_ids: Optional[List[str]] = None,
    removed_ionization_mechanism_ids: Optional[List[str]] = None,
    independent_transaction: bool = False,
    sid: str = None,
    process_id=None,
    parent_id=None,
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
        print("Removing all matches and match interferences")

    # Step 3: Delete matches and match interferences corresponding to these isotopes.
    await delete_matches(sample_item_ids, target_isotope_ids)
    await delete_match_interferences(sample_item_ids, target_isotope_ids)

    # Step 4: Return sample and message
    sample = await get_sample(sample_item_id)
    sample_item_name = sample["sample_item_name"]
    return {
        "data": sample,
        "message": f"Match data for sample '{sample_item_name}' removed.",
        "_notification_data": {"sample_item_id": sample_item_id},
    }


@api_controller_background_task(
    success_notification_rooms=["sample_item_id", "instrument"],
    success_reload=[("sample_batch_reload", "sample_batch_id")],
    error_notification_rooms=["sid"],
    error_reload=[("sample_batch_reload", "sid")],
)
async def match_sample_compute(
    sample_item_id: str,
    added_target_compound_ids: Optional[List[str]] = None,
    added_ionization_mechanism_ids: Optional[List[str]] = None,
    independent_transaction: bool = False,
    sid: str = None,
    process_id=None,
    parent_id=None,
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
    """
    # Step 1: Gather sample information
    sample = await get_sample(sample_item_id)
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

    # Prepare progress user notification.
    notification = UserNotification(
        process_id=process_id,
        parent_id=parent_id,
        type="match_sample_compute",
        status="pending",
        message=f"Computing matches for sample '{sample_item_name}'.",
        # NOTE: Set the internal metadata for the pending user_notifications like
        # room_ids and sid of the user.
        # The _instrument_room is provided separately to skip the check if the user
        # has moved from the room (by not providing sid to emit_user_notification).
        # Internal metadata will be cleaned up the from data in send_progress_user_notification.
        data={
            "sample_item_id": sample_item_id,
            "_room_ids": [sample_item_id],
            "_instrument_room": instrument,
            "_sid": sid,
        },
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
    print(f"...Computing matches for sample {sample_item_name}: {sample_item_id} ...")

    # Skip computation if no new target isotopes are found for this sample item
    if target_isotopes_df.empty or target_isotopes_df is None:
        error_message = "No new target isotopes to compute matches for."
        raise ValueError(error_message)

    # Check if m/z calibration is verified for the sample
    if not verified:
        error_message = f"m/z calibration is not verified for sample file: {filename}. Please try to calibrate the file."
        raise ValueError(error_message)

    # Step 5: Compute matches for the sample if passed all checks,
    await compute_sample_match(sample_pydantic, target_isotopes_df, notification)

    # Step 6: Return sample with computed match data and status message
    sample = await get_sample(sample_item_id)
    sample_item_name = sample["sample_item_name"]
    return {
        "data": sample,
        "message": f"Matches computed for sample '{sample_item_name}'.",
        "_notification_data": {"sample_item_id": sample_item_id},
    }


# -------------------------------------------------------------------
# Batch level
# -------------------------------------------------------------------


@api_controller_background_task(
    success_notification_rooms=["sid"],
    error_notification_rooms=["sid"],
)
async def rematch_batches(
    rematch_batches_body: RematchBatchesBody,
    independent_transaction: bool,
    sid: str,
    process_id=None,
    parent_id=None,
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
    """
    # Initialize variables for tracking overall progress and failures for correct user notifications
    total_batches = len(rematch_batches_body.sample_batches)
    total_number_of_items = 0
    items_per_batch = []

    # Step 1: Collect total items and individual batch items count
    for sample_batch in rematch_batches_body.sample_batches:
        sample_items_info = await get_samples(
            sample_batch_id=sample_batch.sample_batch_id, batch_matches_info=False
        )
        total_number_of_items += sample_items_info["results"]
        items_per_batch.append(sample_items_info["results"])

    # Calculate batch weights based on the number of items per batch
    batch_weights = [
        items / total_number_of_items if total_number_of_items else 0
        for items in items_per_batch
    ]

    # Step 3: Process each batch
    samples_compute_failed_all = []  # to collect failed samples from all batches
    rematched_sample_batch_ids = []  # Collect batch IDs that were rematched
    for batch_index, (sample_batch, batch_weight) in enumerate(
        zip(rematch_batches_body.sample_batches, batch_weights), start=1
    ):
        sample_batch_id = sample_batch.sample_batch_id
        added_target_compound_ids = sample_batch.added_target_compound_ids
        removed_target_compound_ids = sample_batch.removed_target_compound_ids

        notification = UserNotification(
            process_id=process_id,
            type="rematch_batches",
            status="pending",
            message=f"Rematching sample batch {batch_index}/{total_batches}.",
            # NOTE: Set the internal metadata for the pending user_notifications like
            # room_ids and sid of the user.
            # Internal metadata will be cleaned up the from data in send_progress_user_notification.
            data={
                "sample_batch_id": sample_batch_id,
                "_room_ids": [sid],
                "_sid": sid,
                "_batch_weight": batch_weight,
                "_batch_index": batch_index,
            },
        )
        await send_progress_user_notification(notification, 0.2)

        # Create rematching task for the current batch
        task = asyncio.create_task(
            rematch_batch(
                sample_batch_id=sample_batch_id,
                added_target_compound_ids=added_target_compound_ids,
                removed_target_compound_ids=removed_target_compound_ids,
                independent_transaction=False,
                sid=sid,
                process_id=gen_id(8),
                parent_id=process_id,
            )
        )

        # Perform the rematch operation for the current batch
        try:
            task_result = await task
            rematched_sample_batch_ids.append(
                task_result["_notification_data"]["sample_batch_id"]
            )
        except ApiException as e:
            # If the task fails, log the error and continue with the next batch
            if e.status_code == 200:  # Warning ApiException with 2-- code
                # Collect failed samples and continue processing next batches
                samples_compute_failed_all.extend(
                    e.tech_message.get("samples_compute_failed", [])
                )
                rematched_sample_batch_ids.append(
                    e.tech_message.get("sample_batch_id", None)
                )
            else:
                # Log critical error and re-raise exception to stop rematching all batches
                print(f"Critical Error in rematch_batch: {e.user_message}")
                raise e from e

        # Step 4: Aggregate failed samples from the batch for reporting
        # If the task result contains information about failed samples, aggregate this information for all batches
        notification.message = (
            f"Finished rematching sample batch {batch_index}/{total_batches}."
        )
        await send_progress_user_notification(notification, 0.8)

    # If there are any aggregated failed samples from all batches, send the waring notificatoin
    if samples_compute_failed_all:
        user_message = f"Warning during rematching {total_batches} sample batch{'es' if total_batches != 1 else ''}: failed to compute matches for {len(samples_compute_failed_all)} sample{'s' if len(samples_compute_failed_all) != 1 else ''}."
        raise ApiException(
            user_message,
            {
                "sample_batch_ids": rematched_sample_batch_ids,
                "samples_compute_failed": samples_compute_failed_all,
            },
            200,
        )

    # Step 8: Return sample batch data and message
    return {
        "message": f"{total_batches} sample batch{'es' if total_batches != 1 else ''} rematched.",
        "_notification_data": {"sample_batch_ids": rematched_sample_batch_ids},
    }


@api_controller_background_task(
    success_notification_rooms=["sample_batch_id"],
    success_reload=[("sample_batch_reload", "sample_batch_id")],
    error_notification_rooms=["sample_batch_id"],
    error_reload=[("sample_batch_reload", "sample_batch_id")],
)
async def rematch_batch(
    sample_batch_id: str,
    added_target_compound_ids: Optional[List[str]] = None,
    added_ionization_mechanism_ids: Optional[List[str]] = None,
    removed_target_compound_ids: Optional[List[str]] = None,
    removed_ionization_mechanism_ids: Optional[List[str]] = None,
    independent_transaction: bool = False,
    notification: UserNotification = None,
    sid: str = None,
    process_id=None,
    parent_id=None,
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

    :param sample_batch_id: _description_
    :type sample_batch_id: str
    :param added_target_compound_ids: _description_, defaults to None
    :type added_target_compound_ids: Optional[List[str]], optional
    :param added_ionization_mechanism_ids: _description_, defaults to None
    :type added_ionization_mechanism_ids: Optional[List[str]], optional
    :param removed_target_compound_ids: _description_, defaults to None
    :type removed_target_compound_ids: Optional[List[str]], optional
    :param removed_ionization_mechanism_ids: _description_, defaults to None
    :type removed_ionization_mechanism_ids: Optional[List[str]], optional
    :param independent_transaction: _description_, defaults to False
    :type independent_transaction: bool, optional
    :param notification: _description_, defaults to None
    :type notification: UserNotification, optional
    :param sid: _description_, defaults to None
    :type sid: str, optional
    :param process_id: _description_, defaults to None
    :type process_id: _type_, optional
    :param parent_id: _description_, defaults to None
    :type parent_id: _type_, optional
    :raises NotFoundException: _description_
    :return: _description_
    :rtype: _type_
    """
    # Step 1: Retrieve batch data.
    async with async_session() as session:
        sample_batch = await session.get(SampleBatch, sample_batch_id)
        if not sample_batch:
            raise NotFoundException(
                f"Sample batch with ID '{sample_batch_id}' not found"
            )
    sample_batch_name = sample_batch.sample_batch_name
    print(
        f"...Rematching sample batch '{sample_batch_name}' with ID {sample_batch_id} ..."
    )
    # Prepare progress user notification.
    notification = UserNotification(
        process_id=process_id,
        parent_id=parent_id,
        type="rematch_batch",
        status="pending",
        message=f"Rematching sample batch '{sample_batch_name}'.",
        # NOTE: Set the internal metadata for the pending user_notifications like
        # room_ids and sid of the user.
        # Internal metadata will be cleaned up the from data in send_progress_user_notification.
        data={
            "sample_batch_id": sample_batch_id,
            "_room_ids": [sample_batch_id],
            "_sid": sid,
        },
    )

    await send_progress_user_notification(notification)

    # Step 2: Remove existing matches based on provided removed parameters
    if removed_target_compound_ids or removed_ionization_mechanism_ids:
        await match_batch_remove(
            sample_batch_id=sample_batch_id,
            removed_target_compound_ids=removed_target_compound_ids,
            removed_ionization_mechanism_ids=removed_ionization_mechanism_ids,
            independent_transaction=False,
            sid=sid,
            process_id=gen_id(8),
            parent_id=process_id,
        )

    # Step 3: Compute new matches based on provided added parameters
    if added_target_compound_ids or added_ionization_mechanism_ids:
        await match_batch_compute(
            sample_batch_id=sample_batch_id,
            added_target_compound_ids=added_target_compound_ids,
            added_ionization_mechanism_ids=added_ionization_mechanism_ids,
            independent_transaction=False,
            sid=sid,
            process_id=gen_id(8),
            parent_id=process_id,
        )
    # Step 4: Perform a complete rematch if no specific targets are provided
    elif not removed_target_compound_ids and not removed_ionization_mechanism_ids:
        await match_batch_remove(
            sample_batch_id=sample_batch_id,
            independent_transaction=False,
            sid=sid,
            process_id=gen_id(8),
            parent_id=process_id,
        )  # Remove all existing matches
        await match_batch_compute(
            sample_batch_id=sample_batch_id,
            independent_transaction=False,
            sid=sid,
            process_id=gen_id(8),
            parent_id=process_id,
        )  # Compute matches for all targets

    # Step 8: Return sample batch data and message
    return {
        "data": sample_batch.to_dict(),
        "message": f"Sample batch '{sample_batch_name}' was rematched.",
        "_notification_data": {"sample_batch_id": sample_batch_id},
    }


@api_controller_background_task(
    success_notification_rooms=["sample_batch_id"],
    success_reload=[("sample_batch_reload", "sample_batch_id")],
    error_notification_rooms=["sid"],
)
async def match_batch_remove(
    sample_batch_id: str,
    removed_target_compound_ids: Optional[List[str]] = None,
    removed_ionization_mechanism_ids: Optional[List[str]] = None,
    independent_transaction: bool = False,
    sid: str = None,
    process_id=None,
    parent_id=None,
):
    """
    Removes matches associated with a sample batch, optionally filtering by removed target compounds or ionization mechanisms.

    This function deletes matches (and associated match interferences) for a given sample batch. If removed target compound IDs or ionization
    mechanism IDs are provided, the function fetches associated target isotope IDs and deletes matches specific to these isotopes.
    If no filters are provided, all matches for the batch are deleted.

    Steps:
    1. Retrieve batch data and associated sample items.
    2. Determine the target isotope IDs that are associated with the removed compounds or ionization mechanisms.
    3. Execute the deletion of matches and associated interferences based on the identified target isotope IDs or remove all matches if no filters are applied.

    :param sample_batch_id: ID of the sample batch for which matches are to be removed.
    :type sample_batch_id: str
    :param removed_target_compound_ids: List of target compound IDs for which matches are to be removed, optional.
    :type removed_target_compound_ids: Optional[List[str]]
    :param removed_ionization_mechanism_ids: List of ionization mechanism IDs for which matches are to be removed, optional.
    :type removed_ionization_mechanism_ids: Optional[List[str]]
    :param independent_transaction: Flag indicating if the operation should be an independent transaction, default to False.
    :type independent_transaction: bool
    """
    # Step 1: Retrieve batch data and associated sample items.
    async with async_session() as session:
        sample_batch = await session.get(SampleBatch, sample_batch_id)
        if not sample_batch:
            raise NotFoundException(
                f"Sample batch with ID '{sample_batch_id}' not found"
            )

    sample_batch_name = sample_batch.sample_batch_name
    print(
        f"...Removing matches for sampe batch '{sample_batch_name}' with ID {sample_batch_id} ..."
    )
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
        print("Removing all matches and match interferences")

    # Step 3: Delete matches and match interferences corresponding to these isotopes.
    await delete_matches(sample_item_ids, target_isotope_ids)
    await delete_match_interferences(sample_item_ids, target_isotope_ids)

    # Step 4: Return sample batch data and message
    return {
        "data": sample_batch.to_dict(),
        "message": f"Match data for sample batch '{sample_batch_name}' removed.",
        "_notification_data": {"sample_batch_id": sample_batch_id},
    }


@api_controller_background_task(
    success_notification_rooms=["sample_batch_id"],
    success_reload=[("sample_batch_reload", "sample_batch_id")],
    error_notification_rooms=[
        "sample_batch_id"
    ],  # NOTE: send to sample_batch_id for warning notifications
    error_reload=[("sample_batch_reload", "sample_batch_id")],
)
async def match_batch_compute(
    sample_batch_id: str,
    added_target_compound_ids: Optional[List[str]] = None,
    added_ionization_mechanism_ids: Optional[List[str]] = None,
    independent_transaction: bool = False,
    notification: UserNotification = None,
    sid: str = None,
    process_id=None,
    parent_id=None,
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
    :raises ValueError: Raised in cases where match computation cannot proceed due to issues such as unverified m/z calibration or the absence new target isotopes to compute matches for.
    """
    # Step 1: Retrieve all samples associated with the specified sample batch.
    async with async_session() as session:
        # Fetch samples
        result = await session.execute(
            select(Sample).where(Sample.sample_batch_id == sample_batch_id)
        )

        samples = result.scalars().all()

    # Step 2: Retrieve batch data and ionization mechanisms from the batch.
    async with async_session() as session:
        sample_batch = await session.get(SampleBatch, sample_batch_id)
        if not sample_batch:
            raise NotFoundException(
                f"Sample batch with ID '{sample_batch_id}' not found"
            )
    sample_batch_name = sample_batch.sample_batch_name
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

    print(
        f"...Computing matches for sample batch '{sample_batch_name}' with ID {sample_batch_id} ..."
    )
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

    # Step 4: Process each sample item for match computation and send progress user notification.
    samples_compute_failed = []
    total_samples = len(samples)
    for item_index, sample in enumerate(samples):
        # Prepare data for match computation
        sample_pydantic = MatchComputeSample(
            sample_item_id=sample.sample_item_id,
            sample_item_name=sample.sample_item_name,
            sample_batch_id=sample.sample_batch_id,
            filename=sample.filename,
            instrument=sample.instrument,
        )

        # Prepare progress user notification.
        notification = UserNotification(
            process_id=process_id,
            parent_id=parent_id,
            type="match_batch_compute",
            status="pending",
            message=f"Computing matches for sample batch '{sample_batch_name}'.",
            # NOTE: Set the internal metadata for the pending user_notifications like
            # room_ids and sid of the user.
            # Internal metadata will be cleaned up the from data in send_progress_user_notification.
            data={
                "sample_batch_id": sample_batch_id,
                "_room_ids": [sample_batch_id],
                "_sid": sid,
                "_total_samples": total_samples,
                "_item_index": item_index,
            },
        )

        try:
            print(
                f"...Computing matches for sample '{sample.sample_item_name}' with ID {sample.sample_item_id} ..."
            )
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
                error_message = f"No new target isotopes to compute matches for sample '{sample.sample_item_name}'."
                raise ValueError(error_message)

            # Step 5: Compute matches for the sample items that passed all checks,
            # where new target isotopes are identified, m/z calibration is verified.

            await compute_sample_match(
                sample_pydantic, filtered_target_isotopes_df, notification
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
                    "warning_message": str(e),
                }
            )

    # Step 7: If there are any failed samples, raise an exception with the list of failed samples included in the error message
    if samples_compute_failed:
        # raise warning user_notifications (ApiException with 200 code)
        user_message = f"Failed to compute matches for {len(samples_compute_failed)} sample{'s' if len(samples_compute_failed) != 1 else ''} in sample batch '{sample_batch_name}'."

        raise ApiException(
            user_message,
            {
                "sample_batch_id": sample_batch_id,
                "samples_compute_failed": samples_compute_failed,
            },
            200,
        )

    # Step 8: Return sample batch data and message
    return {
        "data": sample_batch.to_dict(),
        "message": f"Matches computed for sample batch '{sample_batch_name}'.",
        "_notification_data": {"sample_batch_id": sample_batch_id},
    }
