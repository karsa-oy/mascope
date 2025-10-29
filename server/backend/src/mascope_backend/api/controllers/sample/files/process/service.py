# pylint: disable=line-too-long
"""
Controller for sample files auto-processing pipeline.

Handles automated creation of ACQUISITION workspaces, batches, and sample items,
processing instrument_config and matching the samples.
"""

import asyncio

from mascope_backend.db import async_session, db_semaphore
from mascope_backend.db.id import gen_id
from mascope_backend.db.models import SampleFile, IonizationMode

from mascope_backend.api.lib.api_features import api_controller_background_task
from mascope_backend.api.lib.exceptions.api_exceptions import (
    NotFoundException,
    ApiException,
)

from mascope_backend.api.new.instrument_configs.schemas import (
    CreateInstrumentConfigBody,
    SetInstrumentConfigBody,
)
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
from mascope_backend.api.controllers.sample.files.sample_files_controller import (
    compute_sample_file_peaks,
)
from mascope_backend.api.controllers.sample.items.sample_items_controller import (
    create_sample_items,
)
from mascope_backend.api.controllers.samples.samples_controller import get_sample
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

from mascope_backend.api.models.sample.batches.sample_batch_pydantic_model import (
    SampleBatchCreate,
)
from mascope_backend.api.models.sample.batches.config import sample_batch_config
from mascope_backend.api.models.sample.items.sample_item_pydantic_model import (
    SampleItemCreate,
)
from mascope_backend.api.new.ionization.modes.util import (
    resolve_ionization_modes_by_peaks,
    resolve_ionization_modes_by_tokens,
)


from mascope_backend.runtime import runtime

# Number of calibration fitting attempts before giving up
# Chosen so that final m/z error tolerance for TOF would be around 1000 ppm
CALIBRATION_ITERATIONS = 7


@api_controller_background_task(
    success_notification_rooms=["instrument"],
    success_reload=[("match_reload", "affected_sample_batch_ids")],
    error_notification_rooms=["instrument"],
    error_reload=[("match_reload", "affected_sample_batch_ids")],
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
    - Validate sample file existence
    - Create a new instrument config and process
    - Get ACQUISITION workspace for the instrument
    - Create ACQUISITION batches and sample items for each sample file ionization mode
    - Compute peak data for the sample file
    - Perform calibration and match computation for created ACQUISITION samples
    - Schedule rematch tasks for other affected samples
    - Return processing results with affected IDs or UI reloads

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

    # --- Validate sample file existence --- #
    async with async_session() as session:
        if not (sample_file := await session.get(SampleFile, sample_file_id)):
            raise NotFoundException(f"Sample file with ID '{sample_file_id}' not found")

    # --- Create a new instrument config and process --- #
    method_file_exists = sample_file.method_file and sample_file.method_file.strip()
    if method_file_exists:
        method_file = sample_file.method_file
    else:
        # Fallback to auto-generated method file name
        timestamp = sample_file.datetime.strftime("%Y-%m-%d %H:%M:%S")
        method_file = f"{timestamp} Acquisition {sample_file.instrument}"

    instrument_config = SetInstrumentConfigBody(
        new_record=CreateInstrumentConfigBody(
            method_file=method_file,
        )
    )

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

    # --- Get ACQUISITION workspace for the instrument --- #
    acquisition_workspace = (
        await get_acquisition_workspace(sample_file.instrument)
    ).get("data")

    # --- Create ACQUISITION batches and sample items for each sample file ionization mode --- #
    acquisition_sample_items, acquisition_sample_batches = (
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
        sample["sample_item_id"] for sample in acquisition_sample_items
    )

    # --- Compute peak data for the sample file --- #
    await compute_sample_file_peaks(
        sample_file_id=sample_file_id,
        if_exists="append",
        independent_transaction=False,
        sid=sid,
        process_id=gen_id(8),
        parent_id=process_id,
    )

    # --- Perform calibration and match computation for created ACQUISITION samples --- #
    for sample_item in acquisition_sample_items:
        sample_item_id = sample_item["sample_item_id"]

        # Get ionization mode to check calibration collection
        async with async_session() as session:
            ionization_mode = await session.get(
                IonizationMode, sample_item["ionization_mode_id"]
            )

        # Perform calibration if calibration collection configured for this ionization mode
        if ionization_mode and ionization_mode.calibration_collection_id:
            # Calibration with retry logic
            mz_calibration_params = calibration_params_factory(sample_item["filename"])
            for i in range(1, CALIBRATION_ITERATIONS + 1):
                try:
                    await calibration_mz_calibrate_sample(
                        sample_item_id=sample_item_id,
                        mz_calibration_params=mz_calibration_params,
                        independent_transaction=False,
                        sid=sid,
                        process_id=gen_id(8),
                        parent_id=process_id,
                    )
                    break
                except ApiException as e:
                    if i == CALIBRATION_ITERATIONS:
                        runtime.logger.error(
                            f"Failed to calibrate m/z with m/z tolerance {mz_calibration_params.mz_error_tolerance} "
                            f"for sample item {sample_item["sample_item_name"]}: {e}"
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
                            f"retrying m/z calibration for sample {sample_item['sample_item_name']} with "
                            f"mz_error_tolerance={mz_calibration_params.mz_error_tolerance}."
                        )
        else:
            runtime.logger.warning(
                f"Skipping m/z calibration for sample '{sample_item['sample_item_name']}': "
                f"Calibration collection is not set for the ionization mode '{ionization_mode.ionization_mode_name}'."
            )

        await match_compute_sample(
            sample_item_id=sample_item_id,
            independent_transaction=False,
            sid=sid,
            instrument=instrument,
            process_id=gen_id(8),
            parent_id=process_id,
        )

    # --- Schedule rematch tasks for other affected samples --- #
    acquisition_sample_item_ids = {
        sample["sample_item_id"] for sample in acquisition_sample_items
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
                sid=sid,
                process_id=gen_id(8),
            )
        )

        runtime.logger.info(
            f"Started independent rematch task for {len(other_affected_sample_item_ids)} affected samples"
        )

    # --- Return processing results with affected IDs for UI reloads --- #
    processed_samples = [
        (await get_sample(sample_item_id=item["sample_item_id"]))["data"]
        for item in acquisition_sample_items
    ]

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
        # Step 1: Generate daily ACQUISITION batch name for this ionization mode
        ion_mode_name = ionization_mode.ionization_mode_name
        batch_name = (
            f"{sample_file.datetime.strftime('%Y-%m-%d')} {ion_mode_name} acquisition"
        )

        # Step 2: Get or create daily ACQUISITION batch for this ionization mode
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
