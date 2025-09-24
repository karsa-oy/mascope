"""
Controller for sample files auto-processing pipeline.

Handles automated creation of ACQUISITION workspaces, batches, and sample items,
processing instrument_config and matching the samples.
"""

import asyncio

from mascope_backend.db import async_session, db_semaphore
from mascope_backend.db.id import gen_id
from mascope_backend.db.models import SampleFile
from mascope_backend.api.lib.api_features import api_controller_background_task
from mascope_backend.api.lib.exceptions.api_exceptions import (
    NotFoundException,
)
from mascope_backend.api.new.instrument_configs.service import resolve_instrument_config
from mascope_backend.api.new.instrument_configs.process.service import (
    process_instrument_config,
)
from mascope_backend.api.controllers.workspace.acquisition.service import (
    get_acquisition_workspace,
)
from mascope_backend.api.controllers.sample.batches.sample_batches_controller import (
    get_sample_batches,
    create_sample_batch,
)
from mascope_backend.api.controllers.samples.samples_controller import get_sample
from mascope_backend.api.controllers.sample.items.sample_items_controller import (
    create_sample_items,
)
from mascope_backend.api.controllers.sample.files.sample_files_controller import (
    compute_sample_file_peaks,
)
from mascope_backend.api.controllers.match.match_controller import (
    match_compute_sample,
    rematch_samples,
)
from mascope_backend.api.models.sample.items.sample_item_pydantic_model import (
    SampleItemCreate,
)
from mascope_backend.api.models.sample.batches.sample_batch_pydantic_model import (
    SampleBatchCreate,
)
from mascope_backend.api.models.sample.batches.config import sample_batch_config
from mascope_backend.api.new.ionization.modes.util import (
    resolve_ionization_modes_by_peaks,
    resolve_ionization_modes_by_tokens,
)


from mascope_backend.runtime import runtime


@api_controller_background_task(
    success_notification_rooms=["instrument"],
    success_reload=[("sample_batch_reload", "affected_sample_batch_ids")],
    error_notification_rooms=["instrument"],
    error_reload=[("sample_batch_reload", "affected_sample_batch_ids")],
)
async def auto_process_sample_file(
    sample_file_id: str,
    independent_transaction: bool = None,
    sid: str | None = None,
    instrument: str | None = None,
    process_id: str | None = None,
) -> dict:
    """
    Main orchestrator for automatic sample file processing pipeline.

    Processes uploaded sample files automatically into ACQUISITION workspaces,
    creating the all data hierarchy if needed.

    Steps:
    1. Validate sample file existence
    2. Handle instrument config assignment (existing or create new) and processing
    3. Get ACQUISITION workspace for the instrument
    4. Create ACQUISITION batches and sample items for each sample file polarity
    5. Compute peak data for the sample file
    6. Perform match computation for created sample items
    7. Schedule rematch tasks for other affected samples
    8. Return processing results with affected IDs or UI reloads

    :param sample_file_id: ID of the uploaded sample file
    :type sample_file_id: str
    :param independent_transaction: Indicates whether this operation should be treated as a standalone transaction.
    :type independent_transaction: bool, optional
    :param sid: Session ID for notifications
    :type sid: str | None, optional
    :param instrument: Instrument name for user notifications to its room
    :type instrument: str | None, optional
    :param process_id: Process ID for tracking
    :type process_id: str | None, optional
    :return: Processing results with affected IDs
    """
    # Initialize collector for affected sample items
    all_affected_sample_item_ids = set()

    # Step 1: Get sample file details and validate existence
    async with async_session() as session:
        if not (sample_file := await session.get(SampleFile, sample_file_id)):
            raise NotFoundException(f"Sample file with ID '{sample_file_id}' not found")

    # Step 2: Handle instrument config assignment (existing or create new) and processing
    instrument_config = await resolve_instrument_config(sample_file)

    process_instrument_config_result = await process_instrument_config(
        filenames=[sample_file.filename],
        instrument_config=instrument_config,
        independent_transaction=False,
        sid=sid,
        process_id=gen_id(8),
        parent_id=process_id,
    )
    # Collect affected items from instrument config processing
    all_affected_sample_item_ids.update(
        process_instrument_config_result["_notification_data"].get(
            "affected_sample_item_ids", []
        )
    )

    # Step 3: Get ACQUISITION workspace for the instrument
    acquisition_workspace = (
        await get_acquisition_workspace(sample_file.instrument)
    ).get("data")

    # Step 4: Create ACQUISITION batches and sample items for each polarity
    acquisition_sample_items, acquisition_sample_batches = (
        await create_acquisition_batches_and_items(
            sample_file=sample_file,
            workspace_id=acquisition_workspace.get("workspace_id"),
        )
    )

    # Extract batch IDs for notifications
    affected_sample_batch_ids = [
        batch.get("sample_batch_id") for batch in acquisition_sample_batches
    ]

    # Add newly created items to affected items collection
    for sample_item in acquisition_sample_items:
        all_affected_sample_item_ids.add(sample_item["sample_item_id"])

    # Step 5: Compute peak data for the sample file
    await compute_sample_file_peaks(
        sample_file_id=sample_file_id,
        if_exists="append",
        independent_transaction=False,
        sid=sid,
        process_id=gen_id(8),
        parent_id=process_id,
    )

    # Step 6: Perform match computation for created ACQUISITION samples
    for sample_item in acquisition_sample_items:
        await match_compute_sample(
            sample_item_id=sample_item.get("sample_item_id"),
            independent_transaction=False,
            sid=sid,
            process_id=gen_id(8),
            parent_id=process_id,
        )

    # Step 7: Create separate independent task to recompute matches for other affected samples
    acquisition_sample_item_ids = [
        item["sample_item_id"] for item in acquisition_sample_items
    ]
    other_affected_sample_item_ids = [
        si_id
        for si_id in all_affected_sample_item_ids
        if si_id not in acquisition_sample_item_ids  # exclude the processed sample
    ]
    if other_affected_sample_item_ids:
        asyncio.create_task(
            rematch_samples(
                sample_item_ids=other_affected_sample_item_ids,
                independent_transaction=True,  # Set to true to handle reloads independently
                sid=sid,
                process_id=gen_id(8),
            )
        )

        runtime.logger.info(
            f"Started independent rematch task for {len(other_affected_sample_item_ids)} affected samples"
        )

    # Step 8: Prepare response with processing results
    processed_samples = []
    for sample_item in acquisition_sample_items:
        sample_result = await get_sample(
            sample_item_id=sample_item.get("sample_item_id")
        )
        processed_samples.append(sample_result["data"])

    return {
        "message": f"Auto-processing complete for {sample_file.filename}, processed {len(processed_samples)} samples.",
        "data": processed_samples,
        "_notification_data": {
            "affected_sample_batch_ids": affected_sample_batch_ids,
            "affected_sample_item_ids": list(all_affected_sample_item_ids),
        },
    }


async def create_acquisition_batches_and_items(
    sample_file: SampleFile, workspace_id: str
) -> tuple[list[dict], list[dict]]:
    """
    Create ACQUISITION batches and sample items for each polarity in sample file.

    For each polarity in the sample file:
    1. Get or create daily ACQUISITION batch in provided acquisition workspace
    2. Create ACQUISITION sample item within the batch
    3. Configure batch with appropriate target collections and ionization mechanisms

    :param sample_file: Sample file record containing polarities and metadata
    :type sample_file: SampleFile
    :param workspace_id: ID of ACQUISITION workspace to create batches in
    :type workspace_id: str
    :return: Tuple of (created sample items, created/retrieved batches)
    :rtype: tuple[list[dict], list[dict]]
    """
    sample_items_to_create = []
    acquisition_sample_batches = []

    async def infer_sample_ionization_modes():
        ionization_modes = []
        # Resolve ionization modes based on tokens in filename
        ionization_modes.extend(await resolve_ionization_modes_by_tokens(sample_file))
        if len(ionization_modes) == len(sample_file.polarity):
            # Found matching ionization modes for all polarities (1 or 2)
            return ionization_modes
        elif len(ionization_modes) > len(sample_file.polarity):
            # Found too many ionization modes, likely overlapping tokens
            raise ValueError(
                f"Found too many matching ionization modes for file {sample_file.filename}. "
                "Configure tokens in ionization settings"
            )
        else:
            raise ValueError(
                f"Not enough ionization mode tokens found for file {sample_file.filename}. "
                "Configure tokens in ionization settings"
            )
            # TODO: Fallback to resolving by peaks if tokens were insufficient
            ionization_modes.extend(
                await resolve_ionization_modes_by_peaks(sample_file)
            )
        return ionization_modes

    runtime.logger.debug(
        f"Inferring ionization modes for sample file {sample_file.filename}"
    )
    inferred_ionization_modes = await infer_sample_ionization_modes()
    runtime.logger.debug(
        f"Inferred {len(inferred_ionization_modes)} ionization modes for sample file "
        f"{sample_file.filename}: {[im.ionization_mode_name for im in inferred_ionization_modes]}"
    )

    for ionization_mode in inferred_ionization_modes:
        # Step 1: Generate daily ACQUISITION batch name for this polarity
        ion_mode_name = ionization_mode.ionization_mode_name
        batch_name = (
            f"{sample_file.datetime.strftime('%Y-%m-%d')} {ion_mode_name} acquisition"
        )

        # Step 2: Get or create daily ACQUISITION batch for this polarity
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

        # Prepare ACQUISITION sample item for this polarity
        sample_items_to_create.append(
            SampleItemCreate(
                sample_batch_id=acquisition_sample_batch["sample_batch_id"],
                filename=sample_file.filename,
                sample_item_name=sample_file.datetime.strftime("%Y-%m-%d %H:%M:%S"),
                sample_item_type="ACQUISITION",
                sample_item_attributes={},
                polarity=ionization_mode.ionization_mode_polarity,
                ionization_mode_id=ionization_mode.ionization_mode_id,
            )
        )
    # Step 3: Create ACQUISITION sample items
    acquisition_sample_items = (
        await create_sample_items(
            sample_items=sample_items_to_create, independent_transaction=True
        )
    ).get("data", [])

    return acquisition_sample_items, acquisition_sample_batches
