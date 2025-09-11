# pylint: disable=line-too-long
"""
Match Controller

This module contains all the functionalities and endpoints related to
the matching/rematching processes and related operations.
"""

import asyncio
from sqlalchemy import select, delete
from mascope_backend.db import async_session
from mascope_backend.db.id import gen_id
from mascope_backend.db.wal.engine import wal_checkpoint
from mascope_backend.db.models import (
    Sample,
    SampleBatch,
    MatchIsotope,
    MatchIon,
    MatchCompound,
    MatchCollection,
    MatchSample,
)
from mascope_backend.api.lib.api_features import (
    api_controller,
    api_controller_background_task,
)
from mascope_backend.api.lib.exceptions.api_exceptions import (
    ApiException,
    NotFoundException,
    raise_api_warning,
)
from mascope_backend.api.controllers.match.lib.match_compute import (
    compute_and_create_sample_match_isotope_data,
)
from mascope_backend.api.controllers.match.lib.match_remove import remove_matches
from mascope_backend.api.controllers.target.lib.fetch.target_isotopes_fetch import (
    fetch_sample_unmatched_target_isotopes,
)
from mascope_backend.api.controllers.match.aggregate.match_aggregate_controller import (
    aggregate_and_create_matches,
)
from mascope_backend.api.controllers.sample.lib.fetch_affected_sample_data import (
    fetch_affected_sample_data,
)
from mascope_backend.api.controllers.sample.lib.sample_modified_timestamps_manager import (
    update_sample_modified_timestamps,
)
from mascope_backend.api.controllers.samples.samples_controller import (
    get_samples,
    get_sample,
)
from mascope_backend.api.controllers.samples.lib.samples_fetch import fetch_sample
from mascope_backend.api.models.match.match_pydantic_model import (
    RematchBatchesBody,
)
from mascope_backend.socket.notifications import (
    UserNotification,
    send_progress_user_notification,
)


from mascope_backend.runtime import runtime


# -------------------------------------------------------------------
# Sample level
# -------------------------------------------------------------------


@api_controller_background_task(
    success_notification_rooms=["sid"],
    success_reload=[("sample_batch_reload", "sample_batch_id")],
    error_notification_rooms=["sid"],
)
async def rematch_sample(
    sample_item_id: str,
    added_target_compound_ids: list[str] | None = None,
    added_ionization_mechanism_ids: list[str] | None = None,
    removed_target_compound_ids: list[str] | None = None,
    removed_ionization_mechanism_ids: list[str] | None = None,
    independent_transaction: bool = False,
    sid: str = None,
    process_id=None,
    parent_id=None,
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
    :type added_target_compound_ids: list[str] | None, optional
    :param added_ionization_mechanism_ids: List of ionization mechanism IDs for which matches need to be computed, defaults to None
    :type added_ionization_mechanism_ids: list[str] | None, optional
    :param removed_target_compound_ids: List of target compound IDs for which matches are to be removed, defaults to None
    :type removed_target_compound_ids: list[str] | None, optional
    :param removed_ionization_mechanism_ids: List of ionization mechanism IDs for which matches are to be removed, defaults to None
    :type removed_ionization_mechanism_ids: list[str] | None, optional
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
    runtime.logger.info(f"...Rematching sample: {sample_item_id} ...")
    # Step 1: Remove existing matches based on provided removed parameters
    if removed_target_compound_ids or removed_ionization_mechanism_ids:
        await match_remove_sample(
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
        compute_result = await match_compute_sample(
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
        await match_remove_sample(
            sample_item_id=sample_item_id,
            independent_transaction=False,
            sid=sid,
            process_id=gen_id(8),
            parent_id=process_id,
        )  # Remove all existing matches
        compute_result = await match_compute_sample(
            sample_item_id=sample_item_id,
            independent_transaction=False,
            sid=sid,
            process_id=gen_id(8),
            parent_id=process_id,
        )  # Compute matches for all targets

    # Step 4: Return rematched sample and message
    sample_data = await get_sample(sample_item_id)
    sample = sample_data.get("data")
    sample_item_name = sample["sample_item_name"]

    # Include match status info in the message if available
    match_compute_info = compute_result.get("message", "") if compute_result else ""
    message = f"Sample '{sample_item_name}' was rematched."
    if match_compute_info:
        message = f"{message} {match_compute_info}"

    return {
        "data": sample,
        "message": message,
        "_notification_data": {
            "sample_item_id": sample_item_id,
        },
    }


@api_controller_background_task(
    success_notification_rooms=["sid"],
    success_reload=[("sample_batch_reload", "affected_sample_batch_ids")],
    error_notification_rooms=["sid"],
    error_reload=[("sample_batch_reload", "affected_sample_batch_ids")],
)
async def rematch_samples(
    sample_item_ids: list[str],
    added_target_compound_ids: list[str] | None = None,
    added_ionization_mechanism_ids: list[str] | None = None,
    removed_target_compound_ids: list[str] | None = None,
    removed_ionization_mechanism_ids: list[str] | None = None,
    independent_transaction: bool = False,
    sid: str = None,
    process_id=None,
    parent_id=None,
) -> dict:
    """
    Performs a rematch of multiple samples by removing and/or computing matches based on the specified parameters.
    Thin wrapper arpund the `rematch_sample` controller.

    This function handles the rematch process of the samples by first removing matches associated with removed
    target compounds or ionization mechanisms and then adding matches for added compounds or mechanisms.
    If no parameters are provided, it performs a complete rematch by removing all existing sample matches and
    recomputing them.

    Steps:
    1. Rematch each sample in seqeuence
    2. Retrieve affected sample/batch IDs for reloads

    :param sample_item_ids: IDs of the sample items for which the rematch is to be performed.
    :type sample_item_ids: list[str]
    :param added_target_compound_ids: List of target compound IDs for which matches need to be computed, defaults to None
    :type added_target_compound_ids: list[str] | None, optional
    :param added_ionization_mechanism_ids: List of ionization mechanism IDs for which matches need to be computed, defaults to None
    :type added_ionization_mechanism_ids: list[str] | None, optional
    :param removed_target_compound_ids: List of target compound IDs for which matches are to be removed, defaults to None
    :type removed_target_compound_ids: list[str] | None, optional
    :param removed_ionization_mechanism_ids: List of ionization mechanism IDs for which matches are to be removed, defaults to None
    :type removed_ionization_mechanism_ids: list[str] | None, optional
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
    # Step 1. rematch each sample in sequence
    for sample_item_id in sample_item_ids:
        await rematch_sample(
            sample_item_id=sample_item_id,
            added_target_compound_ids=added_target_compound_ids,
            added_ionization_mechanism_ids=added_ionization_mechanism_ids,
            removed_target_compound_ids=removed_target_compound_ids,
            removed_ionization_mechanism_ids=removed_ionization_mechanism_ids,
            independent_transaction=False,
            sid=sid,
            process_id=gen_id(8),
            parent_id=process_id,
        )
    # Step 2. Retrieve affected sample item and batch IDs for reloads
    (
        affected_sample_item_ids,
        affected_sample_batch_ids,
        *_,
    ) = await fetch_affected_sample_data(sample_item_ids=sample_item_ids)
    return {
        "message": f"Rematched {len(sample_item_ids)} samples",
        "_notification_data": {
            "affected_sample_item_ids": affected_sample_item_ids,
            "affected_sample_batch_ids": affected_sample_batch_ids,
        },
    }


@api_controller_background_task(
    success_notification_rooms=["sample_batch_id"],
    success_reload=[("sample_batch_reload", "sample_batch_id")],
    error_notification_rooms=["sid"],
)
async def match_remove_sample(
    sample_item_id: str,
    full_remove: bool = False,
    independent_transaction: bool = False,
    sid: str | None = None,
    process_id: str | None = None,
    parent_id: str | None = None,
) -> dict:
    """
    Removes matches for a specific sample.

    By default, performs removal by comparing existing matches against
    current sample-target associations. Use full_remove=True for full removal.

    :param sample_item_id: Unique identifier for the sample
    :type sample_item_id: str
    :param full_remove: If True, removes all matches; if False, removes only orphaned matches, defaults to False.
    :type full_remove: bool
    :param independent_transaction: Flag for transaction handling, defaults to False.
    :type independent_transaction: bool
    :param sid: Session ID for notifications
    :param process_id: Process identifier
    :param parent_id: Parent process identifier
    """
    sample = await fetch_sample(sample_item_id)
    runtime.logger.info(
        f"...{'Fully' if full_remove else 'Partially'} removing matches "
        f"for sample '{sample.sample_item_name}' with ID '{sample_item_id}' ..."
    )
    result = await remove_matches(
        sample=sample,
        full_remove=full_remove,
    )
    status = result.get("status")
    removed_match_isotopes_count = result.get("data", {}).get(
        "removed_match_isotopes_count", 0
    )

    if status == "success":
        await update_sample_modified_timestamps(sample_item_ids=[sample_item_id])
        operation_type = (
            "All matches removed" if full_remove else "Orphaned matches removed"
        )
        message = f"{operation_type} for sample '{sample.sample_item_name}'."
    else:
        message = f"No orphaned matches found for sample '{sample.sample_item_name}' - nothing to remove."

    return {
        "status": status,
        "message": message,
        "data": {
            "removed_match_isotopes_count": removed_match_isotopes_count,
        },
        "_notification_data": {"sample_item_id": sample_item_id},
    }


@api_controller_background_task(
    success_notification_rooms=["sample_item_id", "instrument"],
    success_reload=[("sample_batch_reload", "sample_batch_id")],
    error_notification_rooms=["sample_item_id", "instrument"],
    error_reload=[("sample_batch_reload", "sample_batch_id")],
)
async def match_compute_sample(
    sample_item_id: str,
    independent_transaction: bool = False,
    sid: str | None = None,
    process_id: str | None = None,
    parent_id: str | None = None,
) -> dict:
    """
    Computes new matches for a specific sample by identifying missing target isotope matches.
    - Automatically determines which target isotopes need computation
    - Handles m/z calibration verification and polarity filtering
    - Aggregates higher-level matches based on computed isotopes

    :param sample_item_id: Sample item identifier for match computation
    :type sample_item_id: str
    :param independent_transaction: Controls event emission behavior, defaults to False
    :type independent_transaction: bool, optional
    :param sid: Session identifier for client notifications, defaults to None
    :type sid: str, optional
    :param process_id: Process identifier for progress tracking
    :type process_id: str, optional
    :param parent_id: Parent process identifier
    :type parent_id: str, optional
    :raises ApiException: When sample not found, calibration issues, or no new targets available
    :return: A dictionary with status message.
    :rtype: dict
    """
    # Step 1: Gather sample information
    sample = await fetch_sample(sample_item_id)

    # Step 2: Check if m/z calibration is verified for the sample
    # TODO_calibration split on orbi/tof?
    verified = (
        sample.mz_calibration.get("verified", False)
        if sample.mz_calibration is not None
        else True
    )
    if not verified:
        warning_message = f"m/z calibration is not verified for sample file: {sample.filename}. Please try to calibrate the file."
        raise_api_warning(warning_message, {"sample_item_id": sample_item_id})

    runtime.logger.info(
        f"...Computing match isotopes for sample {sample.sample_item_name}: {sample_item_id} ..."
    )

    # Step 3: Fetch target isotopes needing computation, applies all filters centrally on db lvl
    match_params = await default_match_params(sample_item_id)
    target_isotopes_df = await fetch_sample_unmatched_target_isotopes(
        sample, match_params
    )

    # Step 4: Compute match_isotopes for the sample
    computed_match_isotopes_count = 0
    if target_isotopes_df is not None and not target_isotopes_df.empty:
        progress_notification = UserNotification(
            process_id=process_id,
            parent_id=parent_id,
            type="match_compute_sample",
            status="pending",
            message=f"Computing match isotopes for sample '{sample.sample_item_name}'.",
            # NOTE: Set the internal metadata for the pending user_notifications like
            # room_ids and sid of the user.
            # The _instrument_room is provided separately to skip the check if the user
            # has moved from the room (by not providing sid to emit_user_notification).
            # Internal metadata will be cleaned up the from data in send_progress_user_notification.
            data={
                "sample_item_id": sample_item_id,
                "_room_ids": [sample_item_id],
                "_instrument_room": sample.instrument,
                "_sid": sid,
            },
        )
        match_data = await compute_and_create_sample_match_isotope_data(
            sample, target_isotopes_df, progress_notification
        )
        computed_match_isotopes_count = len(match_data["match_isotopes"])

    # Step 5: Aggregate higher-level matches and update timestamps
    match_aggregate_result = await aggregate_and_create_matches(
        sample_item_id=sample_item_id
    )
    match_aggregate_status = match_aggregate_result.get("status")

    if match_aggregate_status in ("success", "partial"):
        runtime.logger.debug(
            f"Aggregated new higher-level matches for sample '{sample.sample_item_name}'."
        )
        await update_sample_modified_timestamps(sample_item_ids=[sample_item_id])

    # Determine status based on outcomes
    message = f"Finished computing matches ({match_aggregate_status}) for sample '{sample.sample_item_name}'."
    if computed_match_isotopes_count > 0:
        compute_status = "success"
        message += f" Computed {computed_match_isotopes_count} new match isotope{'s' if computed_match_isotopes_count != 1 else ''}."
    else:
        compute_status = "skipped"
        message += (
            f" No new match isotopes found for sample '{sample.sample_item_name}'."
        )

    if match_aggregate_status in ("success", "partial"):
        compute_status = "success"
    else:
        # Nothing computed, nothing aggregated
        compute_status = "skipped"
    message += f" (status: {compute_status})"
    runtime.logger.debug(message)

    # Step 6: Return sample with computed match data and status message
    return {
        "status": compute_status,
        "message": message,
        "_notification_data": {"sample_item_id": sample_item_id},
    }


@api_controller_background_task(
    success_notification_rooms=["sid"],
    success_reload=[("sample_batch_reload", "affected_sample_batch_ids")],
    error_notification_rooms=["sid"],
    error_reload=[("sample_batch_reload", "affected_sample_batch_ids")],
)
async def match_compute_samples(
    sample_item_ids: list[str],
    independent_transaction: bool = False,
    sid: str | None = None,
    process_id: str | None = None,
    parent_id: str | None = None,
) -> dict:
    """
    Computes new matches for multiple samples by processing each individually.
    - Thin wrapper around match_compute_sample for processing sample lists
    - Uses simplified automatic target detection per sample
    - Provides basic progress tracking and error collection

    Steps:
    1. Compute match samples
    2. Retrieve affected sample/batch IDs for reloads

    :param sample_item_ids: ID of the sample item for which matches are to be computed.
    :type sample_item_ids: str
    :param independent_transaction: Flag indicating whether the sample match computing is an independent transaction, which affects event emission, defaults to False
    :type independent_transaction: bool, optional
    :param sid: Session ID, used for targeting specific clients when emitting events, defaults to None
    :type sid: str, optional
    :raises ApiException: Raised when no new target isotopes are available for match computation or if other critical preconditions are not met.
    :return: A dictionary containing the rematched sample object and a status message.
    :rtype: dict
    """
    # Step 1. Compute match samples
    for sample_item_id in sample_item_ids:
        await match_compute_sample(
            sample_item_id=sample_item_id,
            independent_transaction=False,
            sid=sid,
            process_id=gen_id(8),
            parent_id=process_id,
        )
    # Step 2. Retrieve affected sample/batch IDs for reloads
    (
        affected_sample_item_ids,
        affected_sample_batch_ids,
        *_,
    ) = await fetch_affected_sample_data(sample_item_ids=sample_item_ids)
    return {
        "message": f"Match isotopes computed for {len(sample_item_ids)} samples.",
        "_notification_data": {
            "affected_sample_item_ids": affected_sample_item_ids,
            "affected_sample_batch_ids": affected_sample_batch_ids,
        },
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
    3. Process each sample batch sequentially, continuing even if individual batches fail.
    4. Aggregate results including: successful batches, failed samples, and critical errors.
    5. Return status message along with notification data.

    :param rematch_batches_body: A list of sample batch identifiers along with optional removed/added entities
    :type rematch_batches_body: RematchBatchesBody
    :param independent_transaction: Flag to indicate if the operation should be treated as an independent transaction
    :type independent_transaction: bool
    :param sid: Session ID, used for emitting notifications to specific clients
    :type sid: str
    :return: A status message indicating the outcome of the batch rematch operation, including any failed match computations for samples.
    :rtype: dict
    """
    # Initialize variables for tracking overall progress
    total_batches = len(rematch_batches_body.sample_batches)
    total_number_of_items = 0
    items_per_batch = []

    # Results tracking
    samples_compute_failed_all = []  # to collect failed samples from all batches
    rematched_sample_batch_ids = []  # Collect batch IDs that were rematched
    failed_batches = []  # Track batches that failed to rematch

    # Step 1: Collect total items and individual batch items count
    for sample_batch in rematch_batches_body.sample_batches:
        sample_items_info = await get_samples(
            sample_batch_id=sample_batch.sample_batch_id
        )
        total_number_of_items += sample_items_info["results"]
        items_per_batch.append(sample_items_info["results"])

    # Calculate batch weights based on the number of items per batch
    batch_weights = [
        items / total_number_of_items if total_number_of_items else 0
        for items in items_per_batch
    ]

    # Step 2: Process each batch
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
            if task_result is None:
                error_msg = f"There were problems during rematching batch {sample_batch_id}, check the logs above."
                runtime.logger.warning(error_msg)
                failed_batches.append({"batch_id": sample_batch_id, "error": error_msg})
                continue  # Skip to the next batch
            batch_id = task_result.get("_notification_data", {}).get(
                "sample_batch_id", None
            )
            if batch_id:
                rematched_sample_batch_ids.append(batch_id)
        except ApiException as e:
            # If the task fails, log the error and continue with the next batch
            if e.status_code == 200:  # Warning ApiException with 2-- code
                # Collect warning-level failured samples and continue processing next batches
                samples_compute_failed_all.extend(
                    e.tech_message.get("samples_compute_failed", [])
                )
                batch_id = e.tech_message.get("sample_batch_id", None)
                if batch_id:
                    rematched_sample_batch_ids.append(batch_id)
            else:
                # Log critical error but continue with next batch
                error_msg = (
                    f"Critical error in batch {sample_batch_id}: {e.user_message}"
                )
                runtime.logger.error(error_msg)

                failed_batches.append(
                    {"batch_id": sample_batch_id, "error": e.user_message}
                )
        except Exception as e:
            # Handle unexpected errors
            error_msg = (
                f"Unexpected error during rematching batch {sample_batch_id}: {str(e)}"
            )
            runtime.logger.error(error_msg)
            failed_batches.append({"batch_id": sample_batch_id, "error": str(e)})

        # Update proress user notification
        notification.message = (
            f"Finished rematching sample batch {batch_index}/{total_batches}."
        )
        await send_progress_user_notification(notification, 0.8)

    # Step 3: Log summary results
    if failed_batches:
        runtime.logger.warning(
            f"There were problems with rematching {len(failed_batches)} sample batches. "
            f"Check the logs above and try manually rematching after addressing the issues."
        )

    if samples_compute_failed_all:
        runtime.logger.warning(
            f"Failed to compute matches for {len(samples_compute_failed_all)} samples across {len(rematched_sample_batch_ids)} batches"
        )

    runtime.logger.info(
        f"Summary: {len(rematched_sample_batch_ids)}/{total_batches} sample batches successfully rematched"
    )

    # Step 4: Raise appropriate exception based on issues
    if failed_batches or samples_compute_failed_all:
        if failed_batches:
            plural_batch = "es" if total_batches != 1 else ""
            failed_count = len(failed_batches)
            user_message = f"Error during rematching {total_batches} sample batch{plural_batch}: {failed_count} batch{plural_batch if failed_count > 1 else ''} failed with critical errors."
            status_code = 500  # Internal server error for critical issues
        else:
            plural_batch = "es" if total_batches != 1 else ""
            plural_sample = "s" if len(samples_compute_failed_all) != 1 else ""
            user_message = f"Warning during rematching {total_batches} sample batch{plural_batch}: failed to compute matches for {len(samples_compute_failed_all)} sample{plural_sample}."
            status_code = 200  # Warning status code

        raise ApiException(
            user_message,
            {
                "sample_batch_ids": rematched_sample_batch_ids,
                "samples_compute_failed": samples_compute_failed_all,
                "failed_batches": failed_batches,
            },
            status_code,
        )

    # Step 5: Return sample batch data and message
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
    added_target_compound_ids: list[str] | None = None,
    added_ionization_mechanism_ids: list[str] | None = None,
    removed_target_compound_ids: list[str] | None = None,
    removed_ionization_mechanism_ids: list[str] | None = None,
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
    :type added_target_compound_ids: list[str] | None, optional
    :param added_ionization_mechanism_ids: List of ionization mechanism IDs for which matches need to be computed, defaults to None
    :type added_ionization_mechanism_ids: list[str] | None, optional
    :param removed_target_compound_ids: List of target compound IDs for which matches are to be removed, defaults to None
    :type removed_target_compound_ids: list[str] | None, optional
    :param removed_ionization_mechanism_ids: List of ionization mechanism IDs for which matches are to be removed, defaults to None
    :type removed_ionization_mechanism_ids: list[str] | None, optional

    Notes:
        - If `removed_*` parameters are provided, the function removes matches related to these parameters.
        - If `added_*` parameters are provided, the function computes new matches related to these parameters.
        - If no `added_*` or `removed_*` parameters are provided, the function removes all existing matches and computes new matches for all targets.

    :param sample_batch_id: _description_
    :type sample_batch_id: str
    :param added_target_compound_ids: _description_, defaults to None
    :type added_target_compound_ids: list[str] | None, optional
    :param added_ionization_mechanism_ids: _description_, defaults to None
    :type added_ionization_mechanism_ids: list[str] | None, optional
    :param removed_target_compound_ids: _description_, defaults to None
    :type removed_target_compound_ids: list[str] | None, optional
    :param removed_ionization_mechanism_ids: _description_, defaults to None
    :type removed_ionization_mechanism_ids: list[str] | None, optional
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
    runtime.logger.info(
        f"...Rematching sample batch '{sample_batch_name}' with ID '{sample_batch_id}' ..."
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
    compute_result = ""
    if (removed_target_compound_ids and len(removed_target_compound_ids) > 0) or (
        removed_ionization_mechanism_ids and len(removed_ionization_mechanism_ids) > 0
    ):
        await match_remove_batch(
            sample_batch_id=sample_batch_id,
            removed_target_compound_ids=removed_target_compound_ids,
            removed_ionization_mechanism_ids=removed_ionization_mechanism_ids,
            independent_transaction=False,
            sid=sid,
            process_id=gen_id(8),
            parent_id=process_id,
        )
        if not (
            added_target_compound_ids and len(added_target_compound_ids) > 0
        ) and not (
            added_ionization_mechanism_ids and len(added_ionization_mechanism_ids) > 0
        ):
            # matches have been removed using `match_remove_batch`=>`remove_matches`, ensuring that no aggregated match data exists.
            # This allows the use of `aggregate_and_create_matches` without the need for `aggregate_and_recreate_matches`
            # to aggregate and save match_compounds, match_collections and match_samples
            await aggregate_and_create_matches(
                sample_batch_id=sample_batch_id,
                match_ions=False,
            )

    # Step 3: Compute new matches based on provided added parameters
    if (added_target_compound_ids and len(added_target_compound_ids) > 0) or (
        added_ionization_mechanism_ids and len(added_ionization_mechanism_ids) > 0
    ):
        # if added_target_compound_ids or added_ionization_mechanism_ids:
        if not (
            removed_target_compound_ids and len(removed_target_compound_ids) > 0
        ) and not (
            removed_ionization_mechanism_ids
            and len(removed_ionization_mechanism_ids) > 0
        ):
            # Remove match_collections and match_samples to overwrite the aggregates
            await remove_matches(
                sample_batch_id=sample_batch_id,
                match_isotopes=False,
                match_ions=False,
            )
        compute_result = await match_compute_batch(
            sample_batch_id=sample_batch_id,
            added_target_compound_ids=added_target_compound_ids,
            added_ionization_mechanism_ids=added_ionization_mechanism_ids,
            independent_transaction=False,
            sid=sid,
            process_id=gen_id(8),
            parent_id=process_id,
        )

    # Step 5: Perform a complete rematch if no specific targets are provided
    if (
        not (removed_target_compound_ids and len(removed_target_compound_ids) > 0)
        and not (
            removed_ionization_mechanism_ids
            and len(removed_ionization_mechanism_ids) > 0
        )
        and not (added_target_compound_ids and len(added_target_compound_ids) > 0)
        and not (
            added_ionization_mechanism_ids and len(added_ionization_mechanism_ids) > 0
        )
    ):
        await match_remove_batch(
            sample_batch_id=sample_batch_id,
            independent_transaction=False,
            sid=sid,
            process_id=gen_id(8),
            parent_id=process_id,
        )  # Remove all existing matches
        compute_result = await match_compute_batch(
            sample_batch_id=sample_batch_id,
            independent_transaction=False,
            sid=sid,
            process_id=gen_id(8),
            parent_id=process_id,
        )  # Compute matches for all targets

    # Step 6: Perform WAL checkpoint
    await wal_checkpoint()

    # Step 7: Return sample batch data and message

    # Include match status info in the message if available
    message = (
        compute_result.get("message", "")
        if compute_result
        else f"Sample batch '{sample_batch_name}' was rematched."
    )
    return {
        "data": sample_batch.to_dict(),
        "message": message,
        "_notification_data": {"sample_batch_id": sample_batch_id},
    }


@api_controller_background_task(
    success_notification_rooms=["sample_batch_id"],
    success_reload=[("sample_batch_reload", "sample_batch_id")],
    error_notification_rooms=["sid"],
)
async def match_remove_batch(
    sample_batch_id: str,
    full_remove: bool = False,
    independent_transaction: bool = False,
    sid: str | None = None,
    process_id: str | None = None,
    parent_id: str | None = None,
) -> dict:
    """
    Removes matches for all samples in the specified sample batch.

    By default, performs removal by comparing existing matches against
    current sample-target associations. Use full_remove=True for full removal.

    :param sample_batch_id: ID of the sample batch for which matches are to be removed.
    :type sample_batch_id: str
    :param full_remove: If True, removes all matches; if False, removes only orphaned matches, defaults to False.
    :type full_remove: bool
    :param independent_transaction: Flag indicating if the operation should be an independent transaction, default to False.
    :type independent_transaction: bool
    :param sid: Session identifier for client notifications
    :param process_id: Process identifier for progress tracking
    :param parent_id: Parent process identifier
    :return: Batch data with removal results and status message
    :rtype: dict
    """
    # Step 1: Retrieve batch data
    sample_batch = await fetch_sample_batch(sample_batch_id)

    runtime.logger.info(
        f"...{'Fully' if full_remove else 'Partially'} removing matches "
        f"for sample batch '{sample_batch.sample_batch_name}' with ID '{sample_batch_id}' ..."
    )

    # Step 2: Remove match data and associated sample batch.
    result = await remove_matches(sample_batch=sample_batch, full_remove=full_remove)
    status = result.get("status")
    removed_match_isotopes_count = result.get("data", {}).get(
        "removed_match_isotopes_count", 0
    )

    if status == "success":
        await update_sample_modified_timestamps(sample_batch_ids=[sample_batch_id])
        remove_message = f"{f"All {removed_match_isotopes_count}" if full_remove else f"{removed_match_isotopes_count} orphaned"} match isotopes removed"
    else:
        remove_message = "No orphaned matches found"

    message = f"{remove_message} for sample batch '{sample_batch.sample_batch_name}'."
    runtime.logger.debug(f"{message} Operation status: {status}.")
    # Step 4: Return sample batch data and message
    return {
        "status": status,
        "message": message,
        "data": {
            "removed_match_isotopes_count": removed_match_isotopes_count,
        },
        "_notification_data": {"sample_batch_id": sample_batch_id},
    }


@api_controller_background_task(
    success_notification_rooms=["sample_batch_id"],
    success_reload=[("sample_batch_reload", "sample_batch_id")],
    error_notification_rooms=["sample_batch_id"],
    error_reload=[("sample_batch_reload", "sample_batch_id")],
)
async def match_compute_batch(
    sample_batch_id: str,
    independent_transaction: bool = False,
    sid: str | None = None,
    process_id: str | None = None,
    parent_id: str | None = None,
) -> dict:
    """
    Computes new matches for all samples within a batch, processing each sample:
    - Filters which target isotopes need computation
    - Aggregates higher-level matches based on computed isotopes

    :param sample_batch_id: The identifier of the sample batch for which match computation is to be performed.
    :type sample_batch_id: str
    :param independent_transaction: Controls event emission behavior
    :type independent_transaction: bool
    :param sid: Session identifier for client notifications
    :param process_id: Process identifier for progress tracking
    :param parent_id: Parent process identifier
    :raises NotFoundException: When batch not found
    :raises ApiException: When batch has no samples or critical failures occur
    :return: Batch data with computation results and status message
    :rtype: dict
    """
    # Step 1: Retrieve sample batch and all associated samples.
    sample_batch = await fetch_sample_batch(sample_batch_id)

    async with async_session() as session:
        samples = (
            (
                await session.execute(
                    select(Sample).where(Sample.sample_batch_id == sample_batch_id)
                )
            )
            .scalars()
            .all()
        )

    sample_batch_name = sample_batch.sample_batch_name
    total_samples_count = len(samples)

    if total_samples_count == 0:
        message = f"Sample batch '{sample_batch.sample_batch_name}' has no samples"
        runtime.logger.debug(message)
        return {
            "status": "skipped",
            "message": message,
            "data": {
                "computed_samples_count": 0,
                "failed_samples_count": 0,
                "skipped_samples_count": 0,
                "total_samples_count": total_samples_count,
            },
            "_notification_data": {"sample_batch_id": sample_batch_id},
        }

    runtime.logger.info(
        f"Computing matches for sample batch '{sample_batch_name}' ({total_samples_count} samples)"
    )

    # Step 2: Process each sample for match computation
    computed_samples = []
    failed_samples = []
    skipped_samples = []
    for item_index, sample in enumerate(samples):
        try:
            runtime.logger.info(
                f"Computing match isotopes for sample {item_index + 1}/{total_samples_count}: '{sample.sample_item_name}'"
            )
            # Check if m/z calibration (if exists) is verified for the sample
            if sample.mz_calibration and not sample.mz_calibration.get(
                "verified", False
            ):
                skipped_samples.append(sample.sample_item_id)
                runtime.logger.debug(
                    f"Skipped uncalibrated sample '{sample.sample_item_name}': "
                    f"m/z calibration not verified for sample file: {sample.filename}."
                )
                continue

            # Fetch unmatched target isotopes for the sample
            match_params = await default_match_params(sample.sample_item_id)
            target_isotopes_df = await fetch_sample_unmatched_target_isotopes(
                sample, match_params
            )
            if target_isotopes_df is None or target_isotopes_df.empty:
                skipped_samples.append(sample.sample_item_id)
                runtime.logger.info(
                    f"No new target isotopes to compute match isotopes for the sample '{sample.sample_item_name}'."
                )
                continue  # Nothing to compute for this sample

            # Step 3: Compute match_isotopes if the sample has passed all checks.
            progress_notification = UserNotification(
                process_id=process_id,
                parent_id=parent_id,
                type="match_compute_batch",
                status="pending",
                message=f"Processing sample {item_index + 1}/{total_samples_count} in sample batch '{sample_batch_name}'",
                # NOTE: Set the internal metadata for the pending user_notifications like
                # room_ids and sid of the user.
                # Internal metadata will be cleaned up the from data in send_progress_user_notification.
                data={
                    "sample_batch_id": sample_batch_id,
                    "_room_ids": [sample_batch_id],
                    "_sid": sid,
                    "_total_samples": total_samples_count,
                    "_item_index": item_index,
                },
            )
            match_data = await compute_and_create_sample_match_isotope_data(
                sample, target_isotopes_df, progress_notification
            )
            # Track samples with matches
            if not match_data["match_isotopes"].empty:
                computed_samples.append(sample.sample_item_id)

        except ApiException as e:
            runtime.logger.info(
                f"Computing match isotopes for sample '{sample.sample_item_name}' failed: {e}"
            )
            failed_samples.append(sample.sample_item_id)

    # Step 4: Aggregate higher-level matches and update timestamps
    match_aggregate_result = await aggregate_and_create_matches(
        sample_batch_id=sample_batch_id
    )
    match_aggregate_status = match_aggregate_result.get("status")
    if match_aggregate_status in ("success", "partial"):
        runtime.logger.debug(
            f"Aggregated new higher-level matches for sample batch '{sample_batch_name}'."
        )
        await update_sample_modified_timestamps(
            sample_item_ids=match_aggregate_result.get("affected_sample_item_ids", [])
        )

    # Step 5: Determine status based on outcomes
    computed_samples_count = len(computed_samples)
    failed_samples_count = len(failed_samples)
    skipped_samples_count = len(skipped_samples)

    if failed_samples_count > 0 and computed_samples_count == 0:
        status = "failed"  # Only failures, no successes
    elif failed_samples_count > 0 and computed_samples_count > 0:
        status = "partial"  # Mixed results
    elif skipped_samples_count > 0:
        status = "skipped"
    else:
        status = "success"

    message = (
        f"Finished computing matches ({status}) for sample batch '{sample_batch.sample_batch_name}'. "
        f"{computed_samples_count} sample{'s' if computed_samples_count != 1 else ''} processed successfully, "
        f"{failed_samples_count} failed, "
        f"{skipped_samples_count} skipped due to missing calibration or no new targets."
    )
    runtime.logger.debug(message)

    return {
        "status": status,
        "message": message,
        "data": {
            "computed_samples_count": computed_samples_count,
            "failed_samples_count": failed_samples_count,
            "skipped_samples_count": skipped_samples_count,
            "total_samples_count": total_samples_count,
        },
        "_notification_data": {"sample_batch_id": sample_batch_id},
    }


# -------------------------------------------------------------------
# App level
# -------------------------------------------------------------------


@api_controller()
async def match_remove_all():
    """
    Deletes all match data across match-related tables in the database.
    """
    counts = {}
    async with async_session() as session:
        # Deleting match isotopes
        result = await session.execute(delete(MatchIsotope))
        counts["match_isotopes"] = result.rowcount

        # Deleting match ions
        result = await session.execute(delete(MatchIon))
        counts["match_ions"] = result.rowcount

        # Deleting match compounds
        result = await session.execute(delete(MatchCompound))
        counts["match_compounds"] = result.rowcount

        # Deleting match collections
        result = await session.execute(delete(MatchCollection))
        counts["match_collections"] = result.rowcount

        # Deleting match samples
        result = await session.execute(delete(MatchSample))
        counts["match_samples"] = result.rowcount

        # Commit all deletions
        await session.commit()

    message = "All match data has been successfully deleted:"
    for key, value in counts.items():
        message += f" {value} {key},"

    return {"message": message}
