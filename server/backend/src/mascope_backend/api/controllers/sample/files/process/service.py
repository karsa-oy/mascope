# pylint: disable=line-too-long
"""
Controller for sample files auto-processing pipeline.

Handles automated creation of ACQUISITION workspaces, batches, and sample items, and matching the samples.
"""

import asyncio
import traceback

from sqlalchemy import delete, select

from mascope_backend.api.controllers.calibration.calibration_controller import (
    calibration_mz_calibrate_sample,
)
from mascope_backend.api.controllers.calibration.lib.calibration_mz_fit import (
    calibration_params_factory,
)
from mascope_backend.api.controllers.match.match_controller import (
    match_compute_sample,
    rematch_samples,
)
from mascope_backend.api.controllers.sample.batches.sample_batches_controller import (
    create_sample_batch,
    get_sample_batches,
)
from mascope_backend.api.controllers.sample.items.sample_items_controller import (
    create_sample_items,
)
from mascope_backend.api.controllers.sample.lib.fetch_affected_sample_data import (
    fetch_affected_sample_data,
)
from mascope_backend.api.controllers.sample.lib.sample_file_fetch import (
    fetch_sample_file,
)
from mascope_backend.api.controllers.workspace.acquisition.service import (
    get_acquisition_workspace,
)
from mascope_backend.api.lib.api_features import api_controller_background_task
from mascope_backend.api.lib.exceptions.api_exceptions import (
    ApiException,
    raise_api_warning,
)
from mascope_backend.api.models.sample.batches.config import sample_batch_config
from mascope_backend.api.models.sample.batches.sample_batch_pydantic_model import (
    SampleBatchCreate,
)
from mascope_backend.api.models.sample.items.sample_item_pydantic_model import (
    SampleItemCreate,
)
from mascope_backend.api.new.ionization.modes.util import (
    resolve_ionization_modes_by_tokens,
)
from mascope_backend.db import (
    IonizationMode,
    SampleBatch,
    SampleFile,
    SampleItem,
    async_session,
    db_semaphore,
)
from mascope_backend.db.id import gen_id
from mascope_backend.runtime import runtime
from mascope_backend.socket.records.service import (
    emit_record_deleted,
)


# Number of calibration fitting attempts before giving up
# Chosen so that final m/z error tolerance for TOF would be around 1000 ppm
CALIBRATION_ITERATIONS = 7


@api_controller_background_task(
    success_notification_rooms=["instrument"],
    success_reload=[("match", "affected_sample_batch_ids")],
    error_notification_rooms=["instrument"],
    error_reload=[("match", "affected_sample_batch_ids")],
)
async def auto_process_sample_file(
    sample_file_id: str,
    independent_transaction: bool = None,
    user_id: int | None = None,
    process_id: str | None = None,
    parent_id: str | None = None,
) -> dict:
    """
    Main orchestrator for automatic sample file processing pipeline.

    Processes uploaded sample files automatically into ACQUISITION workspaces,
    creating the all data hierarchy if needed.

    Steps:
    - Validate sample file existence
    - Get ACQUISITION workspace for the instrument
    - Create ACQUISITION batches and sample items for each sample file ionization mode
    - Perform calibration and match computation for created ACQUISITION samples
    - Schedule rematch tasks for other affected samples
    - Return processing results with affected IDs or UI reloads

    :param sample_file_id: ID of the uploaded sample file
    :type sample_file_id: str
    :param independent_transaction: Indicates whether this operation should be treated as a standalone transaction.
    :type independent_transaction: bool, optional
    :param user_id: Current user triggered operation (for user notifications)
    :type user_id: int | None, optional
    :param process_id: Process ID for tracking
    :type process_id: str | None, optional
    :param parent_id: Parent process ID for tracking hierarchical processes
    :type parent_id: str | None, optional
    :return: Processing results with affected IDs
    """
    # Initialize collector for affected sample items
    all_affected_sample_item_ids = set()

    # --- Validate sample file existence --- #
    sample_file = await fetch_sample_file(sample_file_id=sample_file_id)

    # --- Get ACQUISITION workspace for the instrument --- #
    acquisition_workspace = (
        await get_acquisition_workspace(sample_file.instrument)
    ).get("data")

    # --- Create ACQUISITION batches and sample items for each sample file ionization mode --- #
    acquisition_samples, acquisition_sample_batches = (
        await create_acquisition_batches_and_items(
            sample_file=sample_file,
            workspace_id=acquisition_workspace.get("workspace_id"),
        )
    )

    # Extract batch and sample IDs for notifications
    affected_sample_batch_ids = [
        batch.get("sample_batch_id") for batch in acquisition_sample_batches
    ]
    all_affected_sample_item_ids.update(
        sample["sample_item_id"] for sample in acquisition_samples
    )

    # --- Perform calibration and match computation for created ACQUISITION samples --- #
    for sample in acquisition_samples:
        sample_item_id = sample["sample_item_id"]

        # Get ionization mode to check calibration collection
        async with async_session() as session:
            ionization_mode = await session.get(
                IonizationMode, sample["ionization_mode_id"]
            )

        # Perform calibration if calibration collection configured for this ionization mode
        if ionization_mode and ionization_mode.calibration_collection_id:
            await calibrate_with_retry(
                sample=sample,
                user_id=user_id,
                process_id=process_id,
            )
        else:
            runtime.logger.warning(
                f"Skipping m/z calibration for sample '{sample['sample_item_name']}': "
                f"Calibration collection is not set for the ionization mode '{ionization_mode.ionization_mode_name}'."
            )

        await match_compute_sample(
            sample_item_id=sample_item_id,
            independent_transaction=False,
            user_id=user_id,
            process_id=gen_id(8),
            parent_id=process_id,
        )

    # --- Schedule rematch tasks for other affected samples --- #
    acquisition_sample_item_ids = {
        sample["sample_item_id"] for sample in acquisition_samples
    }
    # exclude the processed sample
    other_affected_sample_item_ids = (
        all_affected_sample_item_ids - acquisition_sample_item_ids
    )

    if other_affected_sample_item_ids:
        asyncio.create_task(
            rematch_samples(
                sample_item_ids=other_affected_sample_item_ids,
                independent_transaction=True,  # Set to true to handle reloads independently
                user_id=user_id,
                process_id=gen_id(8),
            )
        )

        runtime.logger.info(
            f"Started independent rematch task for {len(other_affected_sample_item_ids)} affected samples"
        )

    # --- Return processed results with affected IDs for UI reloads --- #
    acquisition_samples = (
        await fetch_affected_sample_data(
            sample_item_ids=[
                sample["sample_item_id"] for sample in acquisition_samples
            ],
            include_objects=True,
        )
    ).affected_samples

    return {
        "message": f"Auto-processing complete for {sample_file.filename}, processed {len(acquisition_samples)} samples.",
        "data": acquisition_samples,
        "_notification_data": {
            "affected_sample_batch_ids": affected_sample_batch_ids,
            "affected_sample_item_ids": list(all_affected_sample_item_ids),
            "instrument": sample_file.instrument,
        },
    }


@api_controller_background_task(
    success_notification_rooms=["user_id"],
    success_reload=[("match", "affected_sample_batch_ids")],
    error_notification_rooms=["user_id"],
    error_reload=[("match", "affected_sample_batch_ids")],
)
async def re_process_sample_files(
    sample_file_ids: list[str],
    independent_transaction: bool = False,
    user_id: int | None = None,
    process_id: str | None = None,
) -> dict:
    """
    Re-processes multiple sample files by their unique IDs.

    Steps:
    - Validate all sample files exist and have no user-created samples
    - Delete existing ACQUISITION sample items for all files
    - Run auto-process pipeline for each file
    - Return aggregated results

    :param sample_file_ids: List of IDs of the sample files to re-process
    :type sample_file_ids: list[str]
    :param independent_transaction: Indicates whether this operation should be treated as a standalone transaction.
    :type independent_transaction: bool, optional
    :param user_id: Current user triggered operation (for user notifications)
    :type user_id: int | None, optional
    :param process_id: Process ID for tracking
    :type process_id: str | None, optional
    :return: Processing results with aggregated data
    :rtype: dict
    """
    processed_files = []
    failed_files = []
    affected_sample_batch_ids = set()
    affected_sample_item_ids = set()

    # --- Validate all sample files exist and collect data --- #
    async with async_session() as session:
        result = await session.execute(
            select(SampleFile).where(SampleFile.sample_file_id.in_(sample_file_ids))
        )
        sample_files = result.scalars().all()

    found_ids = {sf.sample_file_id for sf in sample_files}
    missing_ids = set(sample_file_ids) - found_ids

    for missing_id in missing_ids:
        failed_files.append(
            {
                "sample_file_id": missing_id,
                "filename": "unknown",
                "message": f"Sample file with ID '{missing_id}' not found",
            }
        )

    if not sample_files:
        message = f"None of the {len(sample_file_ids)} sample files found"
        raise ApiException(
            user_message=message,
            tech_message={"failed_files": failed_files},
            status_code=404,
        )

    # --- Check for user-created samples --- #
    async with async_session() as session:
        # Query for found_ids
        result = await session.execute(
            select(SampleItem, SampleBatch)
            .join(
                SampleBatch, SampleItem.sample_batch_id == SampleBatch.sample_batch_id
            )
            .where(
                SampleItem.sample_file_id.in_(found_ids),
                SampleItem.sample_item_type != "ACQUISITION",
            )
        )
        user_created_samples = result.all()

    # Map sample_file_id → (sample_item, batch) for fast lookup
    user_samples_dict = {
        sample_item.sample_file_id: (sample_item, batch)
        for sample_item, batch in user_created_samples
    }

    # --- Validate each file --- #
    valid_sample_files = []

    for sample_file in sample_files:
        # Check for user-created samples
        if sample_file.sample_file_id in user_samples_dict:
            sample_item, batch = user_samples_dict[sample_file.sample_file_id]
            failed_files.append(
                {
                    "sample_file_id": sample_file.sample_file_id,
                    "filename": sample_file.filename,
                    "message": (
                        "Cannot re-process file as it is associated with a user-created "
                        f"sample in the batch {batch.sample_batch_name}."
                    ),
                }
            )
            continue

        # Verify ionization modes are defined properly
        try:
            await resolve_ionization_modes_by_tokens(sample_file)
        except ValueError as ve:
            # Ionization mode resolution failed
            failed_files.append(
                {
                    "sample_file_id": sample_file.sample_file_id,
                    "filename": sample_file.filename,
                    "message": str(ve),
                }
            )
            continue
        except Exception as e:  # pylint: disable=broad-except
            # Other unexpected errors
            failed_files.append(
                {
                    "sample_file_id": sample_file.sample_file_id,
                    "filename": sample_file.filename,
                    "message": f"Failed to resolve ionization modes: {str(e)}",
                }
            )
            runtime.logger.error(
                "Unexpected error resolving ionization modes for sample file "
                f"{sample_file.filename}: {e}\n{traceback.format_exc()}"
            )
            continue

        # Passed all validations
        valid_sample_files.append(sample_file)

    # --- Delete existing sample items for valid files --- #
    if valid_sample_files:
        valid_sample_file_ids = {sf.sample_file_id for sf in valid_sample_files}

        async with async_session() as session:
            # Collect existing sample items for notifications
            acquisition_sample_items = (
                (
                    await session.execute(
                        select(SampleItem).where(
                            SampleItem.sample_file_id.in_(valid_sample_file_ids)
                        )
                    )
                )
                .scalars()
                .all()
            )
            # Delete
            await session.execute(
                delete(SampleItem).where(
                    SampleItem.sample_file_id.in_(valid_sample_file_ids)
                )
            )
            await session.commit()

            # Emit deletion notifications
            for sample_item in acquisition_sample_items:
                affected_sample_batch_ids.add(sample_item.sample_batch_id)
                if independent_transaction:
                    await emit_record_deleted(
                        record_type="sample",
                        record_id=sample_item.sample_item_id,
                        room=sample_item.sample_batch_id,
                    )

    # --- Process valid files --- #
    for sample_file in valid_sample_files:
        try:
            result = await auto_process_sample_file(
                sample_file_id=sample_file.sample_file_id,
                independent_transaction=False,
                user_id=user_id,
                process_id=gen_id(8),
                parent_id=process_id,
            )

            processed_files.append(
                {
                    "sample_file_id": sample_file.sample_file_id,
                    "filename": sample_file.filename,
                    "message": f"Successfully processed file {sample_file.filename}.",
                }
            )

            # Collect notification data
            file_notification_data = result.get("_notification_data", {})
            if "affected_sample_batch_ids" in file_notification_data:
                affected_sample_batch_ids.update(
                    file_notification_data["affected_sample_batch_ids"]
                )
            if "affected_sample_item_ids" in file_notification_data:
                affected_sample_item_ids.update(
                    file_notification_data["affected_sample_item_ids"]
                )
        except ApiException as ae:
            failed_files.append(
                {
                    "sample_file_id": sample_file.sample_file_id,
                    "filename": sample_file.filename,
                    "message": f"Processing failed: {ae.user_message}",
                }
            )
        except Exception as e:  # pylint: disable=broad-except
            failed_files.append(
                {
                    "sample_file_id": sample_file.sample_file_id,
                    "filename": sample_file.filename,
                    "message": f"Processing failed: {str(e)}",
                }
            )

    # --- Prepare response --- #
    total_files = len(sample_file_ids)
    processed_count = len(processed_files)
    failed_count = len(failed_files)
    notification_data = {
        "total_files": total_files,
        "processed_files": processed_files,
        "failed_files": failed_files,
        "summary": {
            "processed": processed_count,
            "failed": failed_count,
            "total": total_files,
        },
        "affected_sample_batch_ids": list(affected_sample_batch_ids),
    }
    # Determine status and message
    if failed_count == 0:
        message = f"Successfully re-processed {processed_count} sample files."
        return {
            "message": message,
            "_notification_data": notification_data,
        }
    elif processed_count == 0:
        message = f"Failed to re-process all {total_files} sample files.\n" + "\n".join(
            [f"{failed['filename']}: {failed['message']}" for failed in failed_files]
        )
        raise ApiException(
            user_message=message, tech_message=notification_data, status_code=422
        )
    else:
        message = (
            f"Re-processed {processed_count} files successfully, {failed_count} files failed.\n"
            + "\n".join(
                [
                    f"{failed['filename']}: {failed['message']}"
                    for failed in failed_files
                ]
            )
        )
        raise_api_warning(message, notification_data, status_code=207)


async def create_acquisition_batches_and_items(
    sample_file: SampleFile, workspace_id: str
) -> tuple[list[dict], list[dict]]:
    """
    Create ACQUISITION batches and sample items for each ionization mode of sample file.

    For each ionization mode in the sample file:
    - Get or create daily ACQUISITION batch in provided acquisition workspace
    - Create ACQUISITION sample item within the batch
    - Configure batch with appropriate target collections and ionization mechanisms

    :param sample_file: Sample file record containing polarities and metadata
    :type sample_file: SampleFile
    :param workspace_id: ID of ACQUISITION workspace to create batches in
    :type workspace_id: str
    :return: Tuple of (created sample items, created/retrieved batches)
    :rtype: tuple[list[dict], list[dict]]
    """
    sample_items_to_create = []
    acquisition_sample_batches = []

    ionization_modes = await resolve_ionization_modes_by_tokens(sample_file)

    for ionization_mode in ionization_modes:
        # --- Generate daily ACQUISITION batch name for this ionization mode ---
        ion_mode_name = ionization_mode.ionization_mode_name
        batch_name = (
            f"{sample_file.datetime.strftime('%Y-%m-%d')} {ion_mode_name} acquisition"
        )

        # --- Get or create daily ACQUISITION batch for this ionization mode ---
        # Wrapped the entire get-or-create logic in semaphore to prevent race conditions
        async with db_semaphore:
            # Check if batch already exists
            batch_data = (
                await get_sample_batches(
                    workspace_id=workspace_id,
                    sample_batch_type=["ACQUISITION"],
                    sample_batch_name=batch_name,
                )
            ).get("data", [])

            if len(batch_data) > 1:
                runtime.logger.error(
                    f"Multiple ACQUISITION batches found for {batch_name} with ionization mode {ion_mode_name}, using first one."
                )

            if batch_data:
                acquisition_sample_batch = batch_data[0]
                runtime.logger.debug(
                    f"Using existing ACQUISITION batch: {acquisition_sample_batch['sample_batch_name']}"
                )
            else:
                # Create new ACQUISITION batch
                # Get DIAGNOSTICS and CALIBRATION target collections for ACQUISITION batches
                target_collection_ids = []
                if ionization_mode.diagnostic_collection_id:
                    target_collection_ids.append(
                        ionization_mode.diagnostic_collection_id
                    )
                if ionization_mode.calibration_collection_id:
                    target_collection_ids.append(
                        ionization_mode.calibration_collection_id
                    )

                if not target_collection_ids:
                    runtime.logger.warning(
                        f"No {', '.join(sample_batch_config.ACQUISITION_COLLECTION_TYPES)} target collections found for ACQUISITION batch"
                    )

                # Create new ACQUISITION batch with defined build params
                acquisition_sample_batch = (
                    await create_sample_batch(
                        sample_batch=SampleBatchCreate(
                            workspace_id=workspace_id,
                            sample_batch_name=batch_name,
                            sample_batch_description=f"Auto-generated daily acquisition batch for {sample_file.instrument}",
                            sample_batch_type="ACQUISITION",
                            polarity=ionization_mode.ionization_mode_polarity,
                            target_collection_ids=target_collection_ids,
                        ),
                        independent_transaction=True,
                    )
                ).get("data")

                runtime.logger.debug(
                    f"Created new ACQUISITION batch: {acquisition_sample_batch['sample_batch_name']}"
                )

        acquisition_sample_batches.append(acquisition_sample_batch)

        # Prepare ACQUISITION sample item for this ionization mode
        sample_items_to_create.append(
            SampleItemCreate(
                sample_batch_id=acquisition_sample_batch["sample_batch_id"],
                sample_file_id=sample_file.sample_file_id,
                sample_item_name=sample_file.datetime.strftime("%Y-%m-%d %H:%M:%S"),
                sample_item_type="ACQUISITION",
                sample_item_attributes={},
                polarity=ionization_mode.ionization_mode_polarity,
                ionization_mode_id=ionization_mode.ionization_mode_id,
            )
        )
    # Step 3: Create ACQUISITION sample items
    acquisition_samples = (
        await create_sample_items(
            sample_items=sample_items_to_create, independent_transaction=True
        )
    ).get("data", [])

    return acquisition_samples, acquisition_sample_batches


async def calibrate_with_retry(
    sample: dict, user_id: int | None = None, process_id: str | None = None
) -> None:
    """Calibrate sample with retry logic

    If no matching calibration peaks are found, the m/z error tolerance is doubled
    and the calibration is retried, up to CALIBRATION_ITERATIONS times.

    :param sample: Sample dict to calibrate
    :type sample: dict
    :param user_id: Current user triggered operation (for user notifications)
    :type user_id: int | None, optional
    :param process_id: Process ID for tracking
    :type process_id: str | None, optional
    """
    mz_calibration_params = calibration_params_factory(sample["filename"])
    for i in range(1, CALIBRATION_ITERATIONS + 1):
        try:
            await calibration_mz_calibrate_sample(
                sample_item_id=sample["sample_item_id"],
                mz_calibration_params=mz_calibration_params,
                independent_transaction=False,
                user_id=user_id,
                process_id=gen_id(8),
                parent_id=process_id,
            )
            break
        except ApiException as e:
            if i == CALIBRATION_ITERATIONS:
                runtime.logger.error(
                    f"Failed to calibrate m/z with m/z tolerance {mz_calibration_params.mz_error_tolerance} "
                    f"for sample item {sample["sample_item_name"]}: {e}"
                )
            else:
                # Double the m/z error tolerance, check refinement window limits, then retry
                old_tolerance = mz_calibration_params.mz_error_tolerance
                mz_calibration_params.mz_error_tolerance *= 2
                if (
                    mz_calibration_params.refine_window
                    <= mz_calibration_params.mz_error_tolerance
                ):
                    mz_calibration_params.refine_window = (
                        mz_calibration_params.mz_error_tolerance + 1
                    )
                runtime.logger.warning(
                    f"Not enough calibration peaks with m/z error tolerance {old_tolerance}, "
                    f"retrying m/z calibration for sample {sample["sample_item_name"]} with "
                    f"mz_error_tolerance={mz_calibration_params.mz_error_tolerance}."
                )
