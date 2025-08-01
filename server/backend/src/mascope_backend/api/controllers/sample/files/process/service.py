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
    create_sample_item,
)
from mascope_backend.api.controllers.match.match_controller import (
    match_compute_sample,
    rematch_samples,
)
from mascope_backend.api.controllers.target.collections.target_collections_controller import (
    get_target_collections,
)
from mascope_backend.api.controllers.ionization_mechanisms.ionization_mechanisms_controller import (
    get_ionization_mechanisms,
)
from mascope_backend.api.models.sample.items.sample_item_pydantic_model import (
    SampleItemCreate,
)
from mascope_backend.api.models.sample.batches.sample_batch_pydantic_model import (
    SampleBatchCreate,
    BuildParams,
)
from mascope_backend.api.models.sample.batches.config import sample_batch_config


from mascope_backend.runtime import runtime


@api_controller_background_task(
    success_notification_rooms=["sid"],
    success_reload=[("sample_batch_reload", "affected_sample_batch_ids")],
    error_notification_rooms=["sid"],
    error_reload=[("sample_batch_reload", "affected_sample_batch_ids")],
)
async def auto_process_sample_file(
    sample_file_id: str,
    independent_transaction: bool = None,
    sid: str | None = None,
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
    5. Perform match computation for created sample items
    6. Schedule rematch tasks for other affected samples
    7. Return processing results with affected IDs or UI reloads

    :param sample_file_id: ID of the uploaded sample file
    :type sample_file_id: str
    :param independent_transaction: Indicates whether this operation should be treated as a standalone transaction.
    :type independent_transaction: bool, optional
    :param sid: Session ID for notifications
    :type sid: str | None, optional
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

    proces_instrument_config_result = await process_instrument_config(
        filenames=[sample_file.filename],
        instrument_config=instrument_config,
        independent_transaction=False,
        sid=sid,
        process_id=gen_id(8),
        parent_id=process_id,
    )
    # Collect affected items from instrument config processing
    all_affected_sample_item_ids.update(
        proces_instrument_config_result["_notification_data"].get(
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

    # Step 5: Perform match computation for created ACQUISITION samples
    for sample_item in acquisition_sample_items:
        await match_compute_sample(
            sample_item_id=sample_item.get("sample_item_id"),
            independent_transaction=False,
            sid=sid,
            process_id=gen_id(8),
            parent_id=process_id,
        )

    # Step 6: Create separate independent task to recompute matches for other affected samples
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
                independent_transaction=True,  # Set to true to handle reloads independantly
                sid=sid,
                process_id=gen_id(8),
            )
        )

        runtime.logger.info(
            f"Started independant rematch task for {len(other_affected_sample_item_ids)} affected samples"
        )

    # Step 7: Prepare response with processing results
    processed_samples = []
    for sample_item in acquisition_sample_items:
        sample_result = await get_sample(
            sample_item_id=sample_item.get("sample_item_id")
        )
        processed_samples.append(sample_result["data"])

    return {
        "message": f"Auto-processing complete for {sample_file.filename}, preocessed {len(processed_samples)} samples.",
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
    acquisition_sample_items = []
    acquisition_sample_batches = []

    for polarity in sample_file.polarity:
        # Step 1: Generate daily ACQUISITION batch name for this polarity
        polarity_name = sample_batch_config.get_acquisition_polarity_name(polarity)
        batch_name = (
            f"{sample_file.datetime.strftime('%Y-%m-%d')} {polarity_name} acquisition"
        )

        # Step 2: Get or create daily ACQUISITION batch for this polarity
        # Wrapped the entire get-or-create logic in semaphore to prevent race conditions
        async with db_semaphore:
            # Check if batch already exists
            batch_data = (
                await get_sample_batches(
                    workspace_id=workspace_id,
                    sample_batch_type=["ACQUISITION"],
                    polarity=[polarity],
                    sample_batch_name=batch_name,
                )
            ).get("data", [])

            if len(batch_data) > 1:
                runtime.logger.error(
                    f"Multiple ACQUISITION batches found for {batch_name} with polarity {polarity}, using first one."
                )

            if batch_data:
                acquisition_sample_batch = batch_data[0]
                runtime.logger.debug(
                    f"Using existing ACQUISITION batch: {acquisition_sample_batch['sample_batch_name']}"
                )
            else:
                # Create new ACQUISITION batch
                # Get DIAGNOSTICS target collections for ACQUISITION batches
                diagnostics_collections = await get_target_collections(
                    target_collection_type=sample_batch_config.ACQUISITION_COLLECTION_TYPES,
                )

                target_collection_ids = [
                    tc["target_collection_id"]
                    for tc in diagnostics_collections.get("data", [])
                ]

                if not target_collection_ids:
                    runtime.logger.warning(
                        f"No {', '.join(sample_batch_config.ACQUISITION_COLLECTION_TYPES)} target collections found for ACQUISITION batch"
                    )

                # Get default ionization mechanism IDs for this polarity
                default_ionization_mechanisms_ids = [
                    mechanism["ionization_mechanism_id"]
                    for mechanism in (
                        await get_ionization_mechanisms(
                            ionization_mechanism_polarity=polarity, is_default=True
                        )
                    ).get("data", [])
                ]

                # Create new ACQUISITION batch with defined build params
                acquisition_sample_batch = (
                    await create_sample_batch(
                        sample_batch=SampleBatchCreate(
                            workspace_id=workspace_id,
                            sample_batch_name=batch_name,
                            sample_batch_description=f"Auto-generated daily acquisition batch for {sample_file.instrument}",
                            sample_batch_type="ACQUISITION",
                            polarity=polarity,
                            build_params=BuildParams(
                                calibration_collection=None,  # MVP: no calibration for ACQUISITION
                                ion_mechanisms=default_ionization_mechanisms_ids,
                                calibration_ion_mechanisms=[],
                            ),
                            target_collection_ids=target_collection_ids,
                        ),
                        independent_transaction=True,
                    )
                ).get("data")

                runtime.logger.debug(
                    f"Created new ACQUISITION batch: {acquisition_sample_batch['sample_batch_name']}"
                )

        acquisition_sample_batches.append(acquisition_sample_batch)

        # Step 3: Create ACQUISITION sample item for this polarity
        acquisition_sample_item = (
            await create_sample_item(
                sample_item=SampleItemCreate(
                    sample_batch_id=acquisition_sample_batch["sample_batch_id"],
                    filename=sample_file.filename,
                    sample_item_name=sample_file.datetime.strftime("%Y-%m-%d %H:%M:%S"),
                    sample_item_type="ACQUISITION",
                    sample_item_attributes={},
                    polarity=polarity,
                ),
                independent_transaction=True,
            )
        ).get("data", [])

        acquisition_sample_items.append(acquisition_sample_item)
        runtime.logger.debug(
            f"Created sample item: {acquisition_sample_item['sample_item_name']}"
        )

    return acquisition_sample_items, acquisition_sample_batches
