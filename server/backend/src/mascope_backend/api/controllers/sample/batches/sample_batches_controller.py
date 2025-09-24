# pylint: disable=not-callable
import asyncio
from datetime import datetime, timezone
import pandas as pd

from sqlalchemy import (
    asc,
    desc,
    select,
    func,
    delete,
    and_,
)
from sqlalchemy.orm import joinedload

from mascope_file.name import get_instrument_type
from mascope_signal.peak import get_peak_detector, get_peaks
from mascope_backend.db import async_session
from mascope_backend.db.id import gen_id
from mascope_backend.db.models import (
    Workspace,
    SampleBatch,
    TargetCollectionInSampleBatch,
)
from mascope_backend.socket import sio
from mascope_backend.api.lib.api_features import (
    api_controller,
    api_controller_background_task,
)
from mascope_backend.api.lib.exceptions.api_exceptions import (
    NotFoundException,
    ApiException,
    raise_api_warning,
)
from mascope_backend.api.controllers.match.match_controller import (
    rematch_samples,
    match_compute_samples,
)
from mascope_backend.api.controllers.target.collections.target_collections_controller import (
    get_target_collections,
)
from mascope_backend.api.controllers.target.compounds.target_compounds_controller import (
    get_target_compounds,
)
from mascope_backend.api.controllers.target.ions.target_ions_controller import (
    get_target_ions,
)
from mascope_backend.api.controllers.target.isotopes.target_isotopes_controller import (
    get_target_isotopes,
)
from mascope_backend.api.controllers.target.lib.fetch.target_collections_fetch import (
    validate_collections_for_batch,
)
from mascope_backend.api.controllers.sample.lib.sample_file_fetch import (
    fetch_sample_file,
)
from mascope_backend.api.controllers.sample.lib.sample_items_fetch import (
    fetch_sample_item_ids,
)
from mascope_backend.api.controllers.sample.items.sample_items_controller import (
    create_sample_items,
    copy_sample_items,
)
from mascope_backend.api.controllers.samples.samples_controller import get_sample
from mascope_backend.api.controllers.sample.lib.fetch_affected_sample_data import (
    fetch_affected_sample_data,
)
from mascope_backend.api.controllers.sample.batches.lib.util import (
    detect_update_batch_changes,
)
from mascope_backend.api.controllers.sample.batches.status.service import (
    update_sample_batch_status,
)
from mascope_backend.api.controllers.calibration.calibration_controller import (
    calibration_mz_calibrate_samples,
)
from mascope_backend.api.new.instrument_configs.process.service import (
    process_instrument_config,
)
from mascope_backend.api.new.instrument_configs.lib import (
    read_instrument_functions,
)
from mascope_backend.api.new.instrument_configs.schemas import (
    SetInstrumentConfigBody,
)
from mascope_backend.api.new.ionization.modes.util import (
    resolve_ionization_modes_by_tokens,
)
from mascope_backend.api.models.sample.batches.config import sample_batch_config
from mascope_backend.api.models.sample.batches.sample_batch_pydantic_model import (
    SampleBatchCreate,
    SampleBatchRead,
    SampleBatchUpdate,
)
from mascope_backend.api.models.sample.items.sample_item_pydantic_model import (
    SampleItemCreate,
)
from mascope_backend.api.models.calibration.calibration_pydantic_model import (
    MzCalibrationParams,
)
from mascope_backend.socket.notifications import (
    UserNotification,
    send_progress_user_notification,
)

from mascope_backend.runtime import runtime


@api_controller()
async def get_sample_batches(
    workspace_id: str | None = None,
    sample_batch_name: str | None = None,
    sample_batch_type: list[str] | None = None,
    status: list[str] | None = None,
    polarity: list[str] | None = None,
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
    :param sample_batch_name: Name of the sample batch to filter by, defaults to None.
    :type sample_batch_name: str, optional
    :param sample_batch_type: Type of sample batch to filter by (ACQUISITION or ANALYSIS), defaults to None.
    :type sample_batch_type: list[str], optional
    :param polarity: Polarity to filter by (+, -, or +-), defaults to None.
    :type polarity: list[str], optional
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

        # Step 2: Filter by provided parameters
        if workspace_id:
            stmt = stmt.filter(SampleBatch.workspace_id == workspace_id)

        if sample_batch_name:
            stmt = stmt.filter(SampleBatch.sample_batch_name == sample_batch_name)

        if sample_batch_type:
            stmt = stmt.filter(SampleBatch.sample_batch_type.in_(sample_batch_type))

        if status:
            stmt = stmt.filter(SampleBatch.status.in_(status))

        if polarity:
            stmt = stmt.filter(SampleBatch.polarity.in_(polarity))

        # Step 3: Apply sorting
        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(SampleBatch, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(SampleBatch, sort)))

        # Step 4: Apply pagination
        count_stmt = select(func.count()).select_from(stmt)
        total = await session.scalar(count_stmt)
        stmt = stmt.offset(page * limit).limit(limit)

        # Step 5: Execute the query
        result = await session.execute(stmt)
        sample_batches = result.scalars().all()

    # Step 6: Return the total count and the list of validated sample batches
    return {
        "message": "Sample batches retrieved successfully",
        "results": total,
        "data": [
            SampleBatchRead.model_validate(sample_batch).model_dump()
            for sample_batch in sample_batches
        ],
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
        "data": SampleBatchRead.model_validate(sample_batch).model_dump(),
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
    success_reload_events=[
        ("workspace_reload", "workspace_id"),
    ],  # TODO_reload fix when the reload is working properly
)
async def create_sample_batch(
    sample_batch: SampleBatchCreate,
    independent_transaction: bool = False,
) -> dict:
    """
    Creates a new sample batch with the specified details.
    Validates constraints for ACQUISITION batches.

    Steps:
    1. Validate batch constraints:
        - workspace type constraints for ACQUISITION batches
        - target collection type constraints for the sample batch type
        - ionization mechanism polarity compatibility
    2. Construct a new SampleBatch object with the provided details and a generated unique ID.
    3. Associate the new sample batch with target collections if any are provided in the request.
    4. Commit the transaction to persist the new sample batch in the database.
    5. Return the details of the created sample batch as a dictionary.
    6. If independent_transaction is True, emit a 'workspace_reload' event to workspace_id room.

    :param sample_batch: Data for creating the sample batch.
    :type sample_batch: SampleBatchCreate
    :param independent_transaction: Flag indicating if the operation is an independent transaction, defaults to False.
    :type independent_transaction: bool, optional
    :return: The created sample batch data.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Validate workspace type for ACQUISITION batches
        if sample_batch.sample_batch_type == "ACQUISITION":
            if not (
                workspace := await session.get(Workspace, sample_batch.workspace_id)
            ):
                raise NotFoundException(
                    f"Workspace with ID '{sample_batch.workspace_id}' not found"
                )

            if workspace.workspace_type != "ACQUISITION":
                raise ValueError(
                    "ACQUISITION sample batches can only be created in ACQUISITION workspaces. "
                    f"Workspace '{workspace.workspace_name}' is of type '{workspace.workspace_type}'"
                )

        # Validate target collection type constraints
        await validate_collections_for_batch(
            target_collection_ids=sample_batch.target_collection_ids,
            sample_batch_type=sample_batch.sample_batch_type,
        )

        # Step 2: Construct new sample batch
        new_sample_batch = SampleBatch(
            sample_batch_id=gen_id(16),
            **sample_batch.model_dump(
                exclude={"target_collection_ids"}
            ),  # Exclude collections associations from unpacking
            locked=(
                1
                if sample_batch.sample_batch_type == "ACQUISITION"
                and sample_batch_config.ACQUISITION_AUTO_LOCK
                else 0
            ),  # Auto-lock acquisition
            sample_batch_utc_created=datetime.now(timezone.utc),
        )

        session.add(new_sample_batch)

        # Step3: Associate with target collections if provided
        for target_collection_id in sample_batch.target_collection_ids:
            new_target_collection_in_sample_batch = TargetCollectionInSampleBatch(
                target_collection_id=target_collection_id,
                sample_batch_id=new_sample_batch.sample_batch_id,
            )
            session.add(new_target_collection_in_sample_batch)

        # Step 4: Commit transaction and refresh instance
        await session.commit()
        await session.refresh(new_sample_batch)

    # Step 5: Return created sample batch
    return {
        "message": f"Sample batch '{new_sample_batch.sample_batch_name}' was created.",
        "data": SampleBatchRead.model_validate(new_sample_batch).model_dump(),
    }


@api_controller(
    # TODO_reload fix when the reload is working properly
)
async def update_sample_batch(
    sample_batch_id: str,
    sample_batch_update: SampleBatchUpdate,
    independent_transaction: bool = False,
) -> dict:
    """
    Updates the specified sample batch with new information and associations.
    Changes to ion mechanisms, calibration parameters, or target collections set batch status to "rematch"

    Steps:
    1. Fetch existing batch data and validate existence
    2. Detect changes between current and proposed state
    3. Validate new configurations when changes are detected
    4. Update batch data using automatic basic field handling
    5. Set rematch status when recomputation is needed
    6. Emit appropriate reload events based on change types

    :param sample_batch_id: ID of the sample batch to update
    :type sample_batch_id: str
    :param sample_batch_update: Updated data for the sample batch
    :type sample_batch_update: SampleBatchUpdate
    :param independent_transaction: Controls sio event emission behavior and error handling.
    :type independent_transaction: bool
    :raises NotFoundException: When sample batch is not found
    :raises ValueError: When validation fails
    :return: Updated sample batch data with success message
    :rtype: dict
    """
    # Step 1: Fetch existing batch with target associations
    async with async_session() as session:
        if not (
            batch := await session.get(
                SampleBatch,
                sample_batch_id,
                options=[joinedload(SampleBatch.target_collection)],
            )
        ):
            raise NotFoundException(
                f"Sample batch with ID '{sample_batch_id}' not found"
            )

        # Step 2: Detect changes between current and proposed state
        changes = detect_update_batch_changes(batch, sample_batch_update)

        # Step 3: Validate new configurations when changes detected
        if changes["collections"]:
            # Validate target collection type constraints
            await validate_collections_for_batch(
                target_collection_ids=sample_batch_update.target_collection_ids,
                sample_batch_type=batch.sample_batch_type,
            )

        # Step 4: Update batch data
        basic_fields = sample_batch_update.model_dump(
            exclude={"target_collection_ids"}, exclude_unset=True
        )
        for field, value in basic_fields.items():
            if hasattr(batch, field):
                setattr(batch, field, value)

        # Update complex fields only when changed
        if changes["collections"]:
            # Remove specific collections
            if changes["collections_to_remove"]:
                await session.execute(
                    delete(TargetCollectionInSampleBatch).where(
                        and_(
                            TargetCollectionInSampleBatch.sample_batch_id
                            == sample_batch_id,
                            TargetCollectionInSampleBatch.target_collection_id.in_(
                                changes["collections_to_remove"]
                            ),
                        )
                    )
                )

            # Add specific collections
            for collection_id in changes["collections_to_add"]:
                session.add(
                    TargetCollectionInSampleBatch(
                        target_collection_id=collection_id,
                        sample_batch_id=sample_batch_id,
                    )
                )

        await session.commit()
        await session.refresh(batch)

    # Step 5: Set rematch status when recomputation needed
    needs_rematch = changes["collections"]
    if needs_rematch:
        await update_sample_batch_status(
            sample_batch_ids=[sample_batch_id],
            status="rematch",
            independent_transaction=True,  # TODO_reload fix when the reload is working properly
        )
        batch.status = "rematch"  # update in-memory obj to reflect status change avoid extra db call

    # Step 6: Emit reload events based on change types
    reload_events = []
    if changes["collections"]:
        reload_events.append(sio.emit("targets_all_reload", namespace="/"))
    if changes["name"]:
        reload_events.append(
            sio.emit("workspace_reload", room=batch.workspace_id, namespace="/")
        )
    elif changes["description"]:
        reload_events.append(
            sio.emit("sample_batch_reload", room=sample_batch_id, namespace="/")
        )

    if reload_events:  # TODO_reload remove when the reload is working properly
        await asyncio.gather(*reload_events)

    return {
        "status": "success",
        "message": f"Sample batch '{batch.sample_batch_name}' was updated"
        + (" and flagged for rematch" if needs_rematch else ""),
        "data": SampleBatchRead.model_validate(batch).model_dump(),
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
    success_reload=[("sample_batch_reload", "affected_sample_batch_ids")],
    error_notification_rooms=["sid"],
    error_reload=[("sample_batch_reload", "affected_sample_batch_ids")],
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
    3. Resolve ionization methods for the sample items to be created.
    4. Create provided sample items and save them to the database.
    5. Optionally calibrate the batch using the provided calibration parameters,
        based on the calibrate_batch flag and if the instrument is TOF.
    6. Get all affected batch IDs
    7. Rematch imported sample items.
    8. Create separate independent task to recompute matches for other affected samples
    9. In case of calibration failure, send a notification with information about failed samples.
    10. Return the status message

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
    # Init collector for affected sample items from all child operations
    all_affected_sample_item_ids = set()

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
    instrument_config_result = await process_instrument_config(
        filenames=[item.filename for item in sample_items],
        instrument_config=instrument_config,
        independent_transaction=False,
        sid=sid,
        process_id=gen_id(8),
        parent_id=process_id,
    )

    # Step 3: Resolve ionization methods for the sample items to be created
    for item in sample_items:
        sample_file = await fetch_sample_file(item.filename)
        ionization_modes = await resolve_ionization_modes_by_tokens(sample_file)
        # Filter ionization modes by polarity
        ionization_modes = [
            im
            for im in ionization_modes
            if im.ionization_mode_polarity == item.polarity
        ]
        if not ionization_modes:
            raise ValueError(
                f"Could not resolve ionization mode for file '{item.filename}'. "
                "No valid ionization mode token in the filename for the selected polarity."
            )
        if len(ionization_modes) > 1:
            raise ValueError(
                f"Could not resolve ionization mode for file '{item.filename}'. "
                "Multiple ionization mode tokens matched the filename."
            )
        item.ionization_mode_id = ionization_modes[0].ionization_mode_id

    # Collect affected items from instrument config processing
    all_affected_sample_item_ids.update(
        instrument_config_result["_notification_data"].get(
            "affected_sample_item_ids", []
        )
    )

    await send_progress_user_notification(notification, 0.15)

    # Step 4: Create provided sample items and save to database
    created_sample_items_data = (
        await create_sample_items(
            sample_items=sample_items, independent_transaction=False
        )
    ).get("data", [])
    created_sample_item_ids = [
        item["sample_item_id"] for item in created_sample_items_data
    ]

    # Add created sample items to the rematch set
    all_affected_sample_item_ids.update(created_sample_item_ids)

    notification.message = f"Created {len(sample_items)} sample{'s records' if len(sample_items) > 1 else 'record'}."
    await send_progress_user_notification(notification, 0.2)

    # Step 5: Optionally calibrate batch if calibrate_batch flag is True and instrument is TOF
    calibration_warning = None
    if calibrate_batch and instrument_type == "tof":
        samples_calibrate_failed = []
        try:
            calibration_result = await calibration_mz_calibrate_samples(
                sample_item_ids=created_sample_item_ids,
                mz_calibration_params=mz_calibration_params,
                independent_transaction=False,
                sid=sid,
                process_id=gen_id(8),
                parent_id=process_id,
            )

            # Collect calibration-affected sample items
            all_affected_sample_item_ids.update(
                calibration_result["_notification_data"].get(
                    "affected_sample_item_ids", []
                )
            )

            notification.message = f"Sample batch'{sample_batch_name}' m/z calibrated."
            await send_progress_user_notification(notification, 0.6)
        except ApiException as e:
            if e.status_code == 200:
                # Handle warning case: proceed to ramtch, the not-calibrated samples
                # will be not matched since the calibration is not verified
                samples_calibrate_failed = e.tech_message.get(
                    "samples_calibrate_failed", []
                )
                calibration_warning = e.user_message

                # Collect affected items from warning response
                all_affected_sample_item_ids.update(
                    e.tech_message.get("_notification_data", {}).get(
                        "affected_sample_item_ids", []
                    )
                )
            else:
                # This is a critical error, re-raise it
                raise

    # Step 6. Get all affected batch IDs
    _, affected_sample_batch_ids, *_ = await fetch_affected_sample_data(
        sample_item_ids=list(all_affected_sample_item_ids)
    )

    # Check for spillover effects (affects on other batches)
    other_affected_batches = [
        bid for bid in affected_sample_batch_ids if bid != sample_batch_id
    ]

    if other_affected_batches:
        other_affected_batches_message = (
            f"Import affected {len(other_affected_batches)} other sample batches"
        )
        runtime.logger.info(other_affected_batches_message)
        notification.message += other_affected_batches_message

    # Step 7: Compute matches for all imported samples
    await match_compute_samples(
        sample_item_ids=created_sample_item_ids,
        independent_transaction=False,
        sid=sid,
        process_id=gen_id(8),
        parent_id=process_id,
    )

    notification.message = f"Rematched {len(all_affected_sample_item_ids)} sample items affected by the import."
    await send_progress_user_notification(notification, 0.9)

    # Step 8: Create separate independent task to recompute matches for other affected samples
    other_affected_sample_item_ids = [
        si_id
        for si_id in all_affected_sample_item_ids
        if si_id not in created_sample_item_ids  # exclude the imported samples
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

    # Step 9: Raise a warning if encountered during calibration
    if calibration_warning is not None:
        raise_api_warning(
            calibration_warning,
            {
                "_notification_data": {
                    "affected_sample_batch_ids": affected_sample_batch_ids,
                },
                "samples_calibrate_failed": samples_calibrate_failed,
            },
        )

    # Step 10: Return the status message
    return {
        "message": f"{len(sample_items)} sample{'s' if len(sample_items) > 1 else ''} was imported to the sample batch '{sample_batch_name}'.",
        "_notification_data": {
            "affected_sample_item_ids": list(all_affected_sample_item_ids),
            "affected_sample_batch_ids": affected_sample_batch_ids,
        },
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

    # Step 4: Create a new sample batch with type conversion
    # batch type: ACQUISITION → ANALYSIS, polarity "+" or "-" to "+-".
    new_sample_batch_body = SampleBatchCreate(
        workspace_id=workspace_id,
        sample_batch_name=sample_batch_name,
        sample_batch_description=sample_batch_description,
        sample_batch_type=(
            sample_batch_config.DEFAULT_SAMPLE_BATCH_TYPE
            if original_sample_batch.sample_batch_type == "ACQUISITION"
            else original_sample_batch.sample_batch_type
        ),
        polarity=(
            sample_batch_config.ANALYSIS_POLARITY
            if original_sample_batch.sample_batch_type == "ACQUISITION"
            else original_sample_batch.polarity
        ),
        target_collection_ids=target_collection_ids,
    )

    # Create the new sample batch
    create_sample_batch_result = await create_sample_batch(new_sample_batch_body)
    new_sample_batch = create_sample_batch_result["data"]

    # Step 5: Copy sample items associated with the original sample batch
    await copy_sample_items(
        sample_item_ids=[s.sample_item_id for s in original_sample_batch.sample_item],
        sample_batch_id=new_sample_batch["sample_batch_id"],
        always_copy_matches=True,
        independent_transaction=False,
        sid=sid,
        process_id=gen_id(8),
        parent_id=process_id,
    )

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
    Exports peak data for a specific sample batch to a CSV file. This process involves loading sample files,
    detecting peaks, and compiling peak data into a DataFrame before saving it to a file.

    Steps:
    1. Fetch sample items belonging to the specified sample batch.
    2. Iterate over each sample item, load its file, and perform peak detection.
    3. Compile detected peaks into a DataFrame.
    4. Save the DataFrame to a CSV file named with the sample batch name and current datetime.
    5. If independent_transaction is True, emit a 'batch_export_peak_data_finished' event with the session ID.

    :param sample_batch_id: ID of the original sample batch to be copied.
    :type sample_batch_id: str
    :param independent_transaction: Flag to indicate if the operation should be treated as an independent transaction, defaults to False.
    :type independent_transaction: bool, optional
    :param sid: Session ID for targeting specific clients when emitting events, defaults to None.
    :type sid: str, optional
    """
    # Get sample batch name
    sample_batch_result = await get_sample_batch(sample_batch_id)
    sample_batch = sample_batch_result.get("data")
    sample_batch_name = sample_batch["sample_batch_name"]

    sample_item_ids, _ = await fetch_sample_item_ids(sample_batch_id=sample_batch_id)

    sample_views_dict_list = []
    for sample_item_id in sample_item_ids:
        result = await get_sample(sample_item_id)
        sample_views_dict_list.append(result["data"])

    sample_views_df = pd.DataFrame(sample_views_dict_list)

    peak_data = []
    total_samples = len(sample_views_df)

    for index, row in sample_views_df.iterrows():
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

            await send_progress_user_notification(notification, 0.1)

            peak_detector = get_peak_detector(filename, instrument_functions)
            sample_file = await peak_detector.detect_peaks(if_exists="append")

            # Assign peak abundance units
            instrument_type = get_instrument_type(filename)
            if instrument_type == "orbi":
                unit = "height"
            if instrument_type == "tof":
                unit = "area"

            await send_progress_user_notification(notification, 0.9)

            peak_data_item = get_peaks(sample_file, unit).sum(dim="time").compute()

            await send_progress_user_notification(notification, 1)
        except Exception as e:
            runtime.logger.error(repr(e))
            continue

        for peak in peak_data_item:
            peak_data.append(
                {
                    "mz": peak.mz.item(),
                    "intensity": peak.item(),
                    "unit": "ions" if instrument_type == "tof" else "counts",
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
                    "instrument": row["instrument"],
                }
            )

    dt_str = datetime.now().isoformat().replace("-", "").replace(":", "").split(".")[0]

    peakfile_name = "_".join(
        [dt_str, "peaks", sample_batch_name.replace(" ", "_") + ".csv"]
    )
    runtime.logger.info(f"Writing peak data to file {peakfile_name}")
    # Save peak data to dataframe and then to csv file
    batch_peak_df = pd.DataFrame(peak_data)
    batch_peak_df.to_csv(
        runtime.env.path("temp", peakfile_name),
        index=False,
        sep=";",
    )
    message = f"Peak data for sample batch '{sample_batch_name}' was exported to file '{peakfile_name}'."
    runtime.logger.info(message)

    # Return the status message
    return {
        "message": message,
        "data": {"filename": peakfile_name},
        "_notification_data": {
            "sample_batch_id": sample_batch_id,
            "download": peakfile_name,
        },
    }
