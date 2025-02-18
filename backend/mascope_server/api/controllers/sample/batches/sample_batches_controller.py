import os
from datetime import datetime, timezone
from fastapi import BackgroundTasks
import pandas as pd

from sqlalchemy import (
    asc,
    desc,
    select,
    func,
)
from sqlalchemy.orm import joinedload

from mascope_lib.file_func import get_filestore_path, get_instrument_type
from mascope_lib.peak import detect_peaks, get_peaks

from mascope_server.db import async_session
from mascope_server.db.id import gen_id
from mascope_server.db.models import (
    Workspace,
    SampleBatch,
    TargetCollectionInSampleBatch,
)
from mascope_server.socket import sio
from mascope_server.api.lib.api_features import (
    api_controller,
    api_controller_background_task,
)
from mascope_server.api.lib.exceptions.api_exceptions import (
    NotFoundException,
    ApiException,
    raise_api_warning,
)
from mascope_server.api.controllers.match.match_controller import rematch_batch
from mascope_server.api.controllers.target.collections.target_collections_controller import (
    get_target_collections,
)
from mascope_server.api.controllers.target.compounds.target_compounds_controller import (
    get_target_compounds,
)
from mascope_server.api.controllers.target.ions.target_ions_controller import (
    get_target_ions,
)
from mascope_server.api.controllers.target.isotopes.target_isotopes_controller import (
    get_target_isotopes,
)
from mascope_server.api.controllers.sample.lib.sample_items_fetch import (
    fetch_sample_item_ids,
)
from mascope_server.api.controllers.sample.items.sample_items_controller import (
    create_sample_item,
    copy_sample_item,
)
from mascope_server.api.controllers.samples.samples_controller import get_sample
from mascope_server.api.controllers.calibration.calibration_controller import (
    calibration_mz_calibrate_batch,
)
from mascope_server.api.new.instrument_configs.process.service import (
    process_instrument_config,
)
from mascope_server.api.new.instrument_configs.lib import (
    read_instrument_functions,
)
from mascope_server.api.new.instrument_configs.schemas import (
    SetInstrumentConfigBody,
)
from mascope_server.api.models.sample.batches.sample_batch_pydantic_model import (
    SampleBatchCreateBody,
    SampleBatchUpdateBody,
)
from mascope_server.api.models.sample.items.sample_item_pydantic_model import (
    SampleItemCreate,
)
from mascope_server.api.models.calibration.calibration_pydantic_model import (
    MzCalibrationParams,
)
from mascope_server.socket.notifications import (
    UserNotification,
    send_progress_user_notification,
)


from mascope_server.runtime import runtime


@api_controller()
async def get_sample_batches(
    workspace_id: str = None,
    sort: str = "sample_batch_utc_created",
    order: str = "asc",
    page: int = 0,
    limit: int = 10000,
) -> dict:
    """
    Retrieves a paginated list of sample batches, optionally filtered by workspace ID, and sorted by a specified column.

    Steps:
    1. Construct a SQLAlchemy query to select all sample batches.
    2. Apply optional workspace ID filtering if specified.
    3. Apply sorting based on the provided sort and order parameters.
    4. Apply pagination based on the provided page and limit parameters.
    5. Execute the query to fetch the results.
    6. Convert the results into a list of dictionaries for JSON serialization.

    :param workspace_id: ID of the workspace to filter sample batches by, defaults to None.
    :type workspace_id: str, optional
    :param sort: Column name to sort the results by, defaults to "sample_batch_utc_created".
    :type sort: str, optional
    :param order: Sorting order, "asc" for ascending or "desc" for descending, defaults to "asc".
    :type order: str, optional
    :param page: Page number for pagination, defaults to 0.
    :type page: int, optional
    :param limit: Number of items per page, defaults to 10000.
    :type limit: int, optional
    :return: A dictionary containing the total count of sample batches and a list of sample batch details.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Construct base query
        stmt = select(SampleBatch)

        # Step 2: Filter by workspace_id if provided
        if workspace_id:
            stmt = stmt.filter(SampleBatch.workspace_id == workspace_id)

        # Step 3: Apply sorting
        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(SampleBatch, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(SampleBatch, sort)))

        # Step 4: Apply pagination
        count_stmt = select(func.count()).select_from(  # pylint: disable=not-callable
            stmt
        )
        total = await session.scalar(count_stmt)
        stmt = stmt.offset(page * limit).limit(limit)

        # Step 5: Execute the query
        result = await session.execute(stmt)
        sample_batches = result.scalars().all()

    # Step 6: Convert the results into a list of dictionaries for JSON serialization and return
    return {
        "message": "Sample batches retrieved successfully",
        "results": total,
        "data": [sample_batch.to_dict() for sample_batch in sample_batches],
    }


@api_controller()
async def get_sample_batch(sample_batch_id: str) -> dict:
    """
    Retrieves a single sample batch by its unique ID.

    Steps:
    1. Execute a query to fetch the sample batch with the specified ID.
    2. Check if the sample batch exists. If not, raise a NotFoundException.
    3. Return the sample batch's details as a dictionary.

    :param sample_batch_id: Unique identifier of the sample batch to retrieve.
    :type sample_batch_id: str
    :raises NotFoundException: If the sample batch with the given ID is not found.
    :return: The requested sample batch's details.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Fetch sample batch by ID
        sample_batch = await session.get(SampleBatch, sample_batch_id)

        if not sample_batch:
            # Step 2: If sample batch not found, raise exception
            raise NotFoundException(
                f"Sample batch with ID '{sample_batch_id}' not found"
            )
    # Step 3: Return sample batch details
    return {
        "message": f"Sample batch '{sample_batch.sample_batch_name}' retrieved successfully",
        "data": sample_batch.to_dict(),
    }


@api_controller()
async def get_batch_targets(sample_batch_id: str, deduplicate: bool = False) -> dict:
    """
    Retrieves targets associated with a specific sample batch, including collections, compounds, ions, and isotopes.

    Steps:
    1. Retrieve target collections, compounds, ions, and isotopes using the existing controllers.
    2. Optionally deduplicate the results based on the deduplicate flag.
    3. Return a comprehensive dictionary including counts and details for target collections, compounds, ions, and isotopes.

    :param sample_batch_id: ID of the sample batch for which targets are being retrieved.
    :type sample_batch_id: str
    :param deduplicate: Flag to indicate whether duplicates should be removed.
    :type deduplicate: bool
    :return: A dictionary containing counts and details of associated targets, with a success message.
    :rtype: dict
    """
    # Step 1: Verify existence of sample batch
    sample_batch_result = await get_sample_batch(sample_batch_id)
    sample_batch = sample_batch_result.get("data")
    sample_batch_name = sample_batch["sample_batch_name"]

    # Step 2: Fetch target collections
    collections_response = await get_target_collections(sample_batch_id=sample_batch_id)
    target_collections = collections_response["data"]

    # Step 3: Fetch target compounds
    compounds_response = await get_target_compounds(
        sample_batch_id=sample_batch_id,
        show_target_collection=not deduplicate,
    )
    target_compounds = compounds_response["data"]

    # Step 4: Fetch target ions
    ions_response = await get_target_ions(
        sample_batch_id=sample_batch_id,
        show_target_collection=not deduplicate,
    )
    target_ions = ions_response["data"]

    # Step 5: Fetch target isotopes
    isotopes_response = await get_target_isotopes(
        sample_batch_id=sample_batch_id,
        show_target_collection=not deduplicate,
    )
    target_isotopes = isotopes_response["data"]

    # Step 6: Compile response
    return {
        "message": (
            f"Sample batch '{sample_batch_name}' targets:"
            f"{len(target_collections)} collections, "
            f"{len(target_compounds)} compounds, "
            f"{len(target_ions)} ions, "
            f"{len(target_isotopes)} isotopes."
        ),
        "result": {
            "target_collections": len(target_collections),
            "target_compounds": len(target_compounds),
            "target_ions": len(target_ions),
            "target_isotopes": len(target_isotopes),
        },
        "data": {
            "target_collections": target_collections,
            "target_compounds": list(target_compounds),
            "target_ions": list(target_ions),
            "target_isotopes": list(target_isotopes),
        },
    }


@api_controller(
    emit_reload_events=[
        ("workspace_reload", "workspace_id"),
    ],
)
async def create_sample_batch(
    sample_batch: SampleBatchCreateBody,
    independent_transaction: bool = False,
) -> dict:
    """
    Creates a new sample batch with the specified details. Emits a workspace reload event if the operation is independent.

    Steps:
    1. Construct a new SampleBatch object with the provided details and a generated unique ID.
    2. Add the new sample batch to the session.
    3. Associate the new sample batch with target collections if any are provided in the request.
    4. Commit the transaction to persist the new sample batch in the database.
    5. If independent_transaction is True, emit a 'workspace_reload' event with the workspace ID.
        May be done in the api_controller by providing emit_reload_events.
    6. Return the details of the created sample batch as a dictionary.

    :param sample_batch: Data for creating the sample batch.
    :type sample_batch: SampleBatchCreateBody
    :param independent_transaction: Flag indicating if the operation is an independent transaction, defaults to False.
    :type independent_transaction: bool, optional
    :return: The created sample batch data.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Construct new sample batch
        new_sample_batch = SampleBatch(
            sample_batch_id=gen_id(16),
            workspace_id=sample_batch.workspace_id,
            sample_batch_name=sample_batch.sample_batch_name,
            sample_batch_description=sample_batch.sample_batch_description,
            build_params=sample_batch.build_params.model_dump(),
            sample_batch_utc_created=datetime.now(timezone.utc),
        )
        # Step 2: Add to session
        session.add(new_sample_batch)

        # Step 3: Associate with target collections if provided
        for target_collection_id in sample_batch.target_collection_ids:
            new_target_collection_in_sample_batch = TargetCollectionInSampleBatch(
                target_collection_id=target_collection_id,
                sample_batch_id=new_sample_batch.sample_batch_id,
            )
            session.add(new_target_collection_in_sample_batch)

        # Step 4: Commit transaction and refresh instance
        await session.commit()
        await session.refresh(new_sample_batch)

    # Step 6: Return created sample batch
    return {
        "message": f"Sample batch '{new_sample_batch.sample_batch_name}' was created.",
        "data": new_sample_batch.to_dict(),
    }


@api_controller()
async def update_sample_batch(
    sample_batch_id: str,
    sample_batch_update_body: SampleBatchUpdateBody,
    background_tasks: BackgroundTasks,
    sid: str = None,
    process_id=None,
) -> dict:
    """
    Updates the specified sample batch with new information and associations. It checks for changes in associated target collections
    and ionization mechanisms to determine if a rematch of the sample batch is necessary. If so, it prepares and executes the rematch
    process using background tasks. The function also handles the update of basic information like the batch name and description,
    and emits appropriate events to notify clients of changes.

    Steps:
    1. Fetch the existing sample batch data.
    2. Determine if a rematch is needed based on changes in collections or ionization mechanisms.
    3. Update the basic information of the sample batch and its associations with target collections.
    4. If needed, prepare and execute the rematch, identifying added or removed compounds and ionization mechanisms.
    5. Based on the updates, emit workspace reload or a sample batch reload.

    :param sample_batch_id: ID of the sample batch to be updated.
    :type sample_batch_id: str
    :param sample_batch_update_body: Updated data for the sample batch.
    :type sample_batch_update_body: SampleBatchUpdateBody
    :param background_tasks: Background tasks for asynchronous execution.
    :type background_tasks: BackgroundTasks
    :raises NotFoundException: Raised if the sample batch is not found in the database.
    :raises ApiException: For handling any exceptions that occur during the update process.
    :return: The dict with updated SampleBatch object, reflecting the changes made.
    rtype: dict
    """
    # Flags for determining if a rematch batch is needed
    rematch_compounds = False  # because of changed collections => compounds
    rematch_ion_mechanisms = False  # because of changed ion_mechanisms
    targets_all_reload = False

    # Flags for determining if a reload is needed
    workspace_reload = False  # if name is changed
    sample_batch_reload = False  # if other basic fields changed and no rematch

    # Step 1. Fetch the existing sample batch data, reference as existing_
    # Retrieves the current state of the sample batch from the database.
    async with async_session() as session:
        stmt = (
            select(SampleBatch)
            .options(joinedload(SampleBatch.target_collection))
            .where(SampleBatch.sample_batch_id == sample_batch_id)
        )
        result = await session.execute(stmt)
        existing_sample_batch = result.unique().scalar_one_or_none()
        if not existing_sample_batch:
            raise NotFoundException(
                f"Sample batch with ID '{sample_batch_id}' not found"
            )

        # Step 2: Determine if a rematch is needed based on changes in collections or ion mechanisms
        # Checks for changes in collections and ionization mechanisms.
        new_collections = set(sample_batch_update_body.target_collection_ids)
        existing_collections = {
            item.target_collection_id
            for item in existing_sample_batch.target_collection
        }
        existing_ion_mechanisms = set(
            existing_sample_batch.build_params["ion_mechanisms"]
        )
        new_ion_mechanisms = set(sample_batch_update_body.build_params.ion_mechanisms)

        # Check if target_compounds were added/remoced
        if new_collections != existing_collections:
            rematch_compounds = True

            # Fetch and store the existing sample batch compounds
            batch_compounds_result = await get_target_compounds(
                sample_batch_id=sample_batch_id
            )
            existing_compounds = set(
                tc["target_compound_id"] for tc in batch_compounds_result["data"]
            )

        # Check if ion_mechanisms were added/remoced
        if new_ion_mechanisms != existing_ion_mechanisms:
            rematch_ion_mechanisms = True

        # Step 3: Update the sample batch.
        # Applies the updates to the sample batch and commits to the database.
        update_data = sample_batch_update_body.dict(exclude_unset=True)
        for key, value in update_data.items():
            if key in ["build_params", "target_collection_ids"]:
                continue  # Skip build_params and target_collections assosiations as they are handled separately below
            if key in ["sample_batch_name"]:
                old_name = getattr(existing_sample_batch, key)
                if old_name != value:  # name value changed
                    # set flag to inform clients about sample batch basic fields changes (emit workspace reload event)
                    workspace_reload = True
                    # BUG_reload do we really need to reload whole workspsce for batch name change? Improve listener sample_batch_reload
            if key in ["sample_batch_description"]:
                old_description = getattr(existing_sample_batch, key)
                if old_description != value:  # description value changed
                    # set flag to reload batch
                    sample_batch_reload = True
            setattr(existing_sample_batch, key, value)

        existing_sample_batch.sample_batch_utc_modified = datetime.now(timezone.utc)

        # ensure batch reload is triggered if calibration
        # mechanisms are changed
        existing_calibration_mechanisms = set(
            existing_sample_batch.build_params.get("calibration_ion_mechanisms", [])
        )
        new_calibration_mechanisms = set(
            sample_batch_update_body.build_params.calibration_ion_mechanisms
        )
        if existing_calibration_mechanisms != new_calibration_mechanisms:
            sample_batch_reload = True

        # Update build_params and associations with target collections
        existing_sample_batch.build_params = (
            sample_batch_update_body.build_params.model_dump()
        )

        if "target_collection_ids" in update_data and (
            new_collections != existing_collections
        ):
            targets_all_reload = True
            # Remove all previous associations
            existing_sample_batch.target_collection.clear()
            # Add new associations
            for target_collection_id in new_collections:
                new_target_collection_in_sample_batch = TargetCollectionInSampleBatch(
                    target_collection_id=target_collection_id,
                    sample_batch_id=existing_sample_batch.sample_batch_id,
                )
                session.add(new_target_collection_in_sample_batch)
        # Save changes to the database
        await session.commit()
        await session.refresh(existing_sample_batch)
    # Rename for clarity after updates
    updated_sample_batch = existing_sample_batch

    # Step 4: Prepare and execute rematch if needed
    # Calculates the changes in compounds and ion mechanisms and prepares the data for rematch.
    if rematch_compounds or rematch_ion_mechanisms:
        # Initialize parameters for rematching
        added_target_compound_ids = set()
        added_ionization_mechanism_ids = set()
        removed_target_compound_ids = set()
        removed_ionization_mechanism_ids = set()
        # batch/workspace reload will be done in the end of rematching process
        sample_batch_reload = False

        # Calculate added and removed compounds and ionization mechanisms
        if rematch_compounds:
            # Fetch the enew current sample batch compounds
            batch_compounds_result = await get_target_compounds(
                sample_batch_id=sample_batch_id
            )
            current_compounds = set(
                tc["target_compound_id"] for tc in batch_compounds_result["data"]
            )

            added_target_compound_ids = current_compounds - existing_compounds
            removed_target_compound_ids = existing_compounds - current_compounds
        if rematch_ion_mechanisms:
            # Fetch the new current sample batch data
            async with async_session() as session:
                stmt = (
                    select(SampleBatch)
                    .options(joinedload(SampleBatch.target_collection))
                    .where(SampleBatch.sample_batch_id == sample_batch_id)
                )
                result = await session.execute(stmt)
                current_sample_batch = result.scalars().first()

            current_ion_mechanisms = set(
                current_sample_batch.build_params["ion_mechanisms"]
            )

            added_ionization_mechanism_ids = (
                current_ion_mechanisms - existing_ion_mechanisms
            )
            removed_ionization_mechanism_ids = (
                existing_ion_mechanisms - current_ion_mechanisms
            )

        # create backfround task for rematch_batch process
        background_tasks.add_task(
            rematch_batch,
            sample_batch_id=sample_batch_id,
            added_target_compound_ids=list(added_target_compound_ids),
            removed_target_compound_ids=list(removed_target_compound_ids),
            added_ionization_mechanism_ids=list(added_ionization_mechanism_ids),
            removed_ionization_mechanism_ids=list(removed_ionization_mechanism_ids),
            independent_transaction=True,
            sid=sid,
            process_id=process_id,
        )

    # Step 5: Based on the updates, emit workspace reload or a sample batch reload.
    if workspace_reload:
        # Emit workspace reload event if the name has changed
        await sio.emit(
            "workspace_reload",
            room=updated_sample_batch.workspace_id,
            namespace="/",
        )
    if sample_batch_reload:
        # Emit batch reload event if the description has changed and rematch was not needed
        await sio.emit(
            "sample_batch_reload",
            room=updated_sample_batch.sample_batch_id,
            namespace="/",
        )
    # If there are  changes in samle_batches associations emit an event to inform all clients.
    if targets_all_reload:
        await sio.emit(
            "targets_all_reload",
            namespace="/",
        )
    return {
        "message": f"Sample '{updated_sample_batch.sample_batch_name}' was updated.",
        "data": updated_sample_batch.to_dict(),
    }


@api_controller_background_task(
    success_notification_rooms=["workspace_id"],
    success_reload=[("workspace_reload", "workspace_id")],
    error_notification_rooms=["workspace_id"],
)
async def delete_sample_batch(
    sample_batch_id: str,
    workspace_id: str = None,
    independent_transaction: bool = False,
    sid: str = None,
    process_id=None,
):
    """
    Deletes a sample batch by its unique ID and optionally emits relevant events.

    Steps:
    1. Fetch the sample batch by its ID from the database to verify its existence.
    2. If the sample batch exists, delete it from the session and commit the changes to the database.
    3. If the operation is independent, emit 'delete_finished' and 'workspace_reload' events with the workspace ID.

    :param sample_batch_id: Unique identifier of the sample batch to delete.
    :type sample_batch_id: str
    :param workspace_id: ID of the workspace associated with the sample batch, used for event emission.
    :type workspace_id: str, optional
    :param independent_transaction: Indicates if the deletion should be considered an independent transaction, which affects event emission.
    :type independent_transaction: bool, optional
    :param sid: Session ID, used for targeting specific clients when emitting events.
    :type sid: str, optional
    :raises NotFoundException: If no sample batch is found with the provided ID.

    Note: The event emission for 'delete_finished' and 'workspace_reload' is handled by the api_controller_background_task decorator based on operation success or failure.
    """
    async with async_session() as session:
        # Step 1: Fetch and verify sample batch existence
        sample_batch = await session.get(SampleBatch, sample_batch_id)
        if not sample_batch:
            raise NotFoundException(
                f"Sample batch with ID '{sample_batch_id}' not found"
            )
        # Step 2: Delete sample batch and commit changes
        await session.delete(sample_batch)
        await session.commit()

    return {
        "message": f"Sample batch '{sample_batch.sample_batch_name}' was deleted.",
        "_notification_data": {
            "sample_batch_id": sample_batch_id,
        },
    }


@api_controller_background_task(
    success_notification_rooms=["sid"],
    error_notification_rooms=["sid"],
    error_reload=[("sample_batch_reload", "sample_batch_id")],
)
async def import_sample_items(
    sample_batch_id: str,
    sample_items: list[SampleItemCreate],
    mz_calibration_params: MzCalibrationParams,
    instrument_config: SetInstrumentConfigBody,
    calibrate_batch: bool = True,
    independent_transaction: bool = False,
    sid: str = None,
    process_id=None,
):
    """
    Imports sample items to a specified batch by creating provided sample items,
    optionally calibrating the batch, and computing matches.

    Steps:
    1. Verify that all sample items are for the same instrument.
    2. Process instrument configs for the sample files.
    3. Create provided sample items and save them to the database.
    4. Optionally calibrate the batch using the provided calibration parameters,
        based on the calibrate_batch flag and if the instrument is TOF.
    5. Compute matches for the batch.
    6. In case of calibration failure, send a notification with information about failed samples.
    7. Return the status message

    :param sample_batch_id: ID of the sample batch where sample items will be imported.
    :type sample_batch_id: str
    :param sample_items: List of sample items to be created and imported.
    :type sample_items: List[SampleItemCreate]
    :param mz_calibration_params: Calibration parameters for the batch. If not provided, default values are used.
    :type mz_calibration_params: MzCalibrationParams
    :param instrument_config: Instrument config to use for the imported files.
    :type instrument_config: InstrumentConfigBody
    :param calibrate_batch: A boolean flag to control whether the batch should undergo calibration, defaults to True
    :type calibrate_batch: bool, optional
    :param independent_transaction: Flag to indicate if the operation should be treated as an independent transaction, defaults to False
    :type independent_transaction: bool, optional
    :param sid: Session ID, used for emitting notifications to specific clients, defaults to None.
    :type sid: str, optional
    """
    sample_batch_result = await get_sample_batch(sample_batch_id)
    sample_batch = sample_batch_result.get("data")
    sample_batch_name = sample_batch["sample_batch_name"]

    # Step 1: Verify that all sample items are for the same instrument
    instrument_types = {get_instrument_type(item.filename) for item in sample_items}
    if len(instrument_types) > 1:
        raise ValueError(
            "Importing samples from different instruments is not supported, please import samples for each instrument separately"
        )
    instrument_type = instrument_types.pop()  # Extract the single instrument type

    notification = UserNotification(
        process_id=process_id,
        type="import_sample_items",
        status="pending",
        message=f"Importing {len(sample_items)} sample{'s' if len(sample_items) > 1 else ''}.",
        # NOTE: Set the internal metadata for the pending user_notifications like
        # room_ids and sid of the user.
        # Internal metadata will be cleaned up the from data in send_progress_user_notification.
        data={
            "sample_batch_id": sample_batch_id,
            "_room_ids": [sid],
            "_sid": sid,
        },
    )
    await send_progress_user_notification(notification, 0.1)

    # Step 2: Process instrument configs for the files
    await process_instrument_config(
        filenames=[item.filename for item in sample_items],
        instrument_config=instrument_config,
        independent_transaction=False,
        sid=sid,
        process_id=gen_id(8),
        parent_id=process_id,
    )
    await send_progress_user_notification(notification, 0.15)

    # Step 3: Create provided sample items and save to database
    for sample_item in sample_items:
        await create_sample_item(sample_item=sample_item)

    notification.message = f"Created {len(sample_items)} sample{'s records' if len(sample_items) > 1 else 'record'}."
    await send_progress_user_notification(notification, 0.2)

    # Step 4: Optionally calibrate batch if calibrate_batch flag is True and instrument is TOF
    warning = None
    if calibrate_batch and instrument_type == "tof":
        samples_calibrate_failed = []
        try:
            calibration_mz_calibrate_batch_data = await calibration_mz_calibrate_batch(
                sample_batch_id=sample_batch_id,
                mz_calibration_params=mz_calibration_params,
                independent_transaction=False,
                sid=sid,
                process_id=gen_id(8),
                parent_id=process_id,
            )
            affected_sample_batch_ids = calibration_mz_calibrate_batch_data["data"].get(
                "affected_sample_batch_ids", None
            )
            notification.message = f"Sample batch'{sample_batch_name}' m/z calibrated."
            if len(affected_sample_batch_ids):
                notification.message += f" Calibration affected {len(affected_sample_batch_ids)} other sample batch{'es' if (len(affected_sample_batch_ids)) > 1 else ''}."
            await send_progress_user_notification(notification, 0.6)
        except ApiException as e:
            if e.status_code == 200:
                # This is a warning, proceed to ramtch, the not-calibrated samples will be not matched
                # since the calibration is not verified
                samples_calibrate_failed = e.tech_message.get(
                    "samples_calibrate_failed", []
                )
                warning = e.user_message
            else:
                # This is a critical error, re-raise it
                raise

    # Step 5: Compute matches for the batch, this would reload the current batch, the other affected_sample_batch_ids reloaded in the calibration_mz_calibrate_batch
    await rematch_batch(
        sample_batch_id=sample_batch_id,
        independent_transaction=False,
        sid=sid,
        process_id=gen_id(8),
        parent_id=process_id,
    )

    notification.message = f"Sample batch'{sample_batch_name}' rematched."
    await send_progress_user_notification(notification, 0.95)

    # Step 6: Raise a warning if encountered during batch calibration
    if warning is not None:
        raise_api_warning(
            warning,
            {
                "sample_batch_id": sample_batch_id,
                "samples_calibrate_failed": samples_calibrate_failed,
            },
        )

    # Step 7: Return the status message
    return {
        "message": f"{len(sample_items)} sample{'s' if len(sample_items) > 1 else ''} was imported to the sample batch '{sample_batch_name}'.",
        "_notification_data": {"sample_batch_id": sample_batch_id},
    }


@api_controller_background_task(
    success_notification_rooms=["workspace_id"],
    success_reload=[("workspace_reload", "workspace_id")],
    error_notification_rooms=["sid"],
    error_reload=[("workspace_reload", "workspace_id")],
)
async def copy_sample_batch(
    sample_batch_id: str,
    workspace_id: str,
    sample_batch_name: str,
    sample_batch_description: str,
    independent_transaction: bool = False,
    sid=None,
    process_id=None,
) -> dict:
    """
    Copies a sample batch, including its associated sample items and target collections, into a specified workspace with a new name and description.
    The function ensures all related entities like sample items and target collections are also copied over to maintain the integrity of the sample batch data.
    Called as a background task from the endpoint, so it also handles sio notification and workspace reloading upon successful copying or if any errors occur.

    Steps:
    1. Validate the workspace into which the sample batch is being copied.
    2. Fetch and validate the original sample batch from the database.
    3. Prepare TargetCollectionInSampleBatch records associated with the original sample batch.
    4. Create a new sample batch with updated information and copy all other data.
    5. Copy associated sample items from the original to the new sample batch.

    :param sample_batch_id: ID of the original sample batch to be copied.
    :type sample_batch_id: str
    :param workspace_id: ID of the workspace where the new sample batch will be placed.
    :type workspace_id: str
    :param sample_batch_name: Name for the new copied sample batch.
    :type sample_batch_name: str
    :param sample_batch_description: Description for the new copied sample batch.
    :type sample_batch_description: str
    :param independent_transaction: Flag to indicate if the operation should be treated as an independent transaction, defaults to False
    :type independent_transaction: bool, optional
    :param sid: Session ID, used for emitting notifications to specific clients, defaults to None.
    :type sid: str, optional
    :raises NotFoundException: If the workspace or original sample batch is not found.
    """
    async with async_session() as session:
        # Step 1: Validate the workspace into which the sample batch is being copied.
        workspace = await session.get(Workspace, workspace_id)

        if not workspace:
            raise NotFoundException(f"Workspace with ID '{workspace_id}' not found")

        # Step 2: Fetch and validate the original sample batch from the database with related TargetCollectionInSampleBatch and SampleItem records
        stmt = (
            select(SampleBatch)
            .options(
                joinedload(SampleBatch.target_collection),
                joinedload(SampleBatch.sample_item),
            )
            .filter(SampleBatch.sample_batch_id == sample_batch_id)
        )
        result = await session.execute(stmt)
        original_sample_batch = result.scalars().first()

        if not original_sample_batch:
            raise NotFoundException(
                f"Sample batch with ID '{sample_batch_id}' not found"
            )

    # Step 3: Prepare TargetCollectionInSampleBatch records associated with the original sample batch
    target_collection_ids = [
        tc.target_collection_id for tc in original_sample_batch.target_collection
    ]

    # Step 4: Create a new sample batch with a new ID, name, description, workspace and time of creation, but copy all other data
    # Form SampleBatchCreateBody instance with new details
    new_sample_batch_body = SampleBatchCreateBody(
        workspace_id=workspace_id,
        sample_batch_name=sample_batch_name,
        sample_batch_description=sample_batch_description,
        build_params=original_sample_batch.build_params,
        target_collection_ids=target_collection_ids,
    )

    # Create the new sample batch
    create_sample_batch_result = await create_sample_batch(new_sample_batch_body)
    new_sample_batch = create_sample_batch_result["data"]

    # Step 5: Copy sample items associated with the original sample batch
    total_samples = len(original_sample_batch.sample_item)
    for item_index, sample_item in enumerate(original_sample_batch.sample_item):
        notification = UserNotification(
            process_id=process_id,
            type="copy_sample_batch",
            status="pending",
            message=f"Copying sample {item_index + 1}/{total_samples} to new batch.",
            data={
                "sample_batch_id": new_sample_batch["sample_batch_id"],
                "_room_ids": [sid],
                "_sid": sid,
                "_total_samples": total_samples,
                "_item_index": item_index,
            },
        )
        await send_progress_user_notification(notification, 0.2)
        await copy_sample_item(
            sample_item_id=sample_item.sample_item_id,
            sample_item_name=sample_item.sample_item_name,
            sample_batch_id=new_sample_batch["sample_batch_id"],
            sid=sid,
            process_id=gen_id(8),
            parent_id=process_id,
        )
        await send_progress_user_notification(notification, 0.9)

    # Step 6: Return the copied batch and message
    sample_batch_name = new_sample_batch["sample_batch_name"]
    new_sample_batch_id = new_sample_batch["sample_batch_id"]
    return {
        "data": new_sample_batch,
        "message": f"Sample batch '{sample_batch_name}' was successfully copied to workspace '{workspace.workspace_name}'.",
        "_notification_data": {
            "sample_item_id": new_sample_batch_id,
            "workspace_id": workspace_id,
        },
    }


@api_controller_background_task(
    success_notification_rooms=["sid"],
    error_notification_rooms=["sid"],
)
async def sample_batch_export_peaks(
    sample_batch_id: str,
    independent_transaction: bool = False,
    sid=None,
    process_id=None,
    parent_id=None,
):
    """
    Exports peak data for a specific sample batch to a parquet file. This process involves loading sample files,
    detecting peaks, and compiling peak data into a DataFrame before saving it to a file.

    Steps:
    1. Fetch sample items belonging to the specified sample batch.
    2. Iterate over each sample item, load its file, and perform peak detection.
    3. Compile detected peaks into a DataFrame.
    4. Save the DataFrame to a parquet file named with the sample batch name and current datetime.
    5. If independent_transaction is True, emit a 'batch_export_peak_data_finished' event with the session ID.

    :param sample_batch_id: ID of the original sample batch to be copied.
    :type sample_batch_id: str
    :param independent_transaction: Flag to indicate if the operation should be treated as an independent transaction, defaults to False.
    :type independent_transaction: bool, optional
    :param sid: Session ID for targeting specific clients when emitting events, defaults to None.
    :type sid: str, optional
    """
    # Get sample batch name
    async with async_session() as session:
        sample_batch = await session.get(SampleBatch, sample_batch_id)
        sample_batch_name = sample_batch.sample_batch_name

    sample_item_ids, _ = await fetch_sample_item_ids(sample_batch_id=sample_batch_id)

    sample_items_dict_list = []
    for sample_item_id in sample_item_ids:
        result = await get_sample(sample_item_id)
        sample_items_dict_list.append(result["data"])

    sample_items_df = pd.DataFrame(sample_items_dict_list)

    peak_data = []
    total_samples = len(sample_items_df)

    for index, row in sample_items_df.iterrows():
        # Prepare progress user notification.
        notification = UserNotification(
            process_id=process_id,
            parent_id=parent_id,
            type="sample_batch_export_peaks",
            status="pending",
            message=f"Exporting peak data for batch '{sample_batch_name}'.",
            # NOTE set the internal room_ids for the pending user_notifications and sid of the user, will be removed from the data.
            data={
                "_room_ids": [sid],
                "_sid": sid,
                "_total_samples": total_samples,
                "_item_index": index,
            },
        )

        try:
            filename = row["filename"]
            instrument_functions = await read_instrument_functions(filename=filename)
            instrument_type = get_instrument_type(filename)

            await send_progress_user_notification(notification, 0.1)

            # Assign peak fitting threshold and peak abundance units
            # depending on the instrument type
            # Correct intrument type unsured by get_instrument_type
            if instrument_type == "orbi":
                threshold = 0.8
                unit = "height"
            if instrument_type == "tof":
                threshold = 0.9
                unit = "area"
            sample_file = await detect_peaks(
                filename,
                instrument_functions,
                threshold,
                u_list=None,
                if_exists="append",
                instrument_type=instrument_type,
            )

            await send_progress_user_notification(notification, 0.9)

            peak_data_item = get_peaks(sample_file, unit).sum(dim="time")

            await send_progress_user_notification(notification, 1)
        except Exception as e:
            runtime.logger.error(repr(e))
            continue

        for peak in peak_data_item:
            peak_data.append(
                {
                    "mz": peak.mz.item(),
                    "intensity": peak.item(),
                    "unit": unit,
                    "sample_batch_name": sample_batch_name,
                    "sample_item_name": row["sample_item_name"],
                    "filename": row["filename"],
                    "filter_id": row["filter_id"],
                    "sample_item_type": row["sample_item_type"],
                    "datetime": row["datetime"],
                    "datetime_utc": row["datetime_utc"],
                    "sample_file_id": row["sample_file_id"],
                    "sample_item_id": row["sample_item_id"],
                    "tic": row["tic"],
                    "instrument": instrument_type,
                }
            )

    dt_str = datetime.now().isoformat().replace("-", "").replace(":", "").split(".")[0]

    peakfile_path = get_filestore_path()
    peakfile_filename = "_".join(
        [dt_str, "peaks", sample_batch_name.replace(" ", "_") + ".csv"]
    )
    runtime.logger.info(f"Writing peak data to file {peakfile_filename}")
    # Save peak data to dataframe and then to csv file
    batch_peak_df = pd.DataFrame(peak_data)
    batch_peak_df.to_csv(
        os.path.join(peakfile_path, peakfile_filename), index=False, sep=";"
    )
    runtime.logger.info("Write complete")

    # Return the status message
    return {
        "message": f"Peak data for sample batch '{sample_batch_name}' was exported to file '{peakfile_filename}' and saved to '{peakfile_path}'.",
        "_notification_data": {
            "sample_batch_id": sample_batch_id,
        },
    }
