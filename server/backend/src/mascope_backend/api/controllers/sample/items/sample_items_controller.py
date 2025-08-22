from datetime import datetime, timezone
from fastapi import BackgroundTasks

import numpy as np
import pandas as pd
from sqlalchemy import (
    insert,
    select,
    delete,
    asc,
    desc,
    func,
)

from mascope_file.name import get_instrument_type

import mascope_signal.compute as m_compute
from mascope_signal.peak import detect_peaks
from mascope_match import (
    ORBI_FITTING_THRESHOLD,
    TOF_FITTING_THRESHOLD,
)

from mascope_backend.socket import sio
from mascope_backend.socket.notifications import (
    UserNotification,
    send_progress_user_notification,
)
from mascope_backend.db import async_session
from mascope_backend.db.id import gen_id
from mascope_backend.db.models import (
    SampleBatch,
    SampleItem,
    SampleFile,
)
from mascope_backend.api.lib.utils import generate_copy_name
from mascope_backend.api.lib.api_features import (
    api_controller,
    api_controller_background_task,
)
from mascope_backend.api.lib.exceptions.api_exceptions import (
    NotFoundException,
)
from mascope_backend.api.controllers.sample.lib.sample_batches_fetch import (
    fetch_sample_batch_data,
)
from mascope_backend.api.controllers.samples.samples_controller import get_sample
from mascope_backend.api.controllers.sample.lib.sample_items_copy import (
    copy_sample_items_match_data,
    CopyMatches,
)
from mascope_backend.api.controllers.samples.lib.samples_fetch import fetch_sample
from mascope_backend.api.controllers.sample.lib.fetch_affected_sample_data import (
    fetch_affected_sample_data,
)
from mascope_backend.api.controllers.match.match_controller import match_compute_samples
from mascope_backend.api.models.sample.items.config import sample_item_config
from mascope_backend.api.models.sample.items.sample_item_pydantic_model import (
    SampleItemBase,
    SampleItemCreate,
    SampleItemRead,
    SampleItemUpdate,
)
from mascope_backend.api.new.instrument_configs.lib import read_instrument_functions
from mascope_backend.api.new.instrument_configs.service import get_instrument_config
from mascope_backend.api.new.instrument_configs.schemas import (
    SetInstrumentConfigBody,
)
from mascope_backend.api.new.instrument_configs.process.service import (
    process_instrument_config,
)

from mascope_backend.runtime import runtime


@api_controller()
async def get_sample_items(
    sample_batch_id: str | None = None,
    filename: str | None = None,
    sample_item_type: list[str] | None = None,
    polarity: list[str] | None = None,
    sort: str = "sample_item_utc_created",
    order: str = "asc",
    page: int = 0,
    limit: int = 10000,
) -> dict:
    """
    Retrieves a paginated list of sample items, optionally sorted by a specified column in either ascending or descending order.

    Steps:
    1. Construct a SQLAlchemy query to select all sample items.
    2. Apply filtering if specified by the parameters.
    3. Apply sorting if specified by the sort and order parameters.
    3. Apply pagination based on the page and limit parameters.
    4. Execute the query to fetch the results.
    5. Convert the results into a list of dictionaries for JSON serialization.

    :param sample_batch_id: The sample batch ID for which you want to fetch the sample items, defaults to None
    :type sample_batch_id: str, optional
    :param filename: The filename for which you want to fetch the sample items, defaults to None
    :type filename: str, optional
    :param sample_item_type: Filter by sample item types, can specify multiple types, defaults to None
    :type sample_item_type: list[str] | None
    :param polarity: Filter by ion polarity mode of the sample item, '+' for positive or '-' for negative
    :type polarity: list[str] | None
    :param sort:  Column to sort by, defaults to "sample_item_utc_created"
    :type sort: str, optional
    :param order: Sorting order ('asc' for ascending, 'desc' for descending), defaults to "asc"
    :type order: str, optional
    :param page: Page number for pagination.
    :type page: int, optional
    :param limit: Number of items per page.
    :type limit: int, optional
    :return: A dictionary with the total count and a list of sample items.
    :rtype: dict
    """
    async with async_session() as session:
        stmt = select(SampleItem)

        # Step 1: Apply filters if specified
        if sample_batch_id:
            stmt = stmt.filter(SampleItem.sample_batch_id == sample_batch_id)

        if filename:
            stmt = stmt.filter(SampleItem.filename == filename)

        if sample_item_type:
            stmt = stmt.filter(SampleItem.sample_item_type.in_(sample_item_type))

        if polarity:
            stmt = stmt.filter(SampleItem.polarity.in_(polarity))

        # Step 2: Apply sorting if specified
        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(SampleItem, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(SampleItem, sort)))

        # Step 3: Get total count for pagination
        count_stmt = select(func.count()).select_from(  # pylint: disable=not-callable
            stmt
        )
        total = await session.scalar(count_stmt)

        # Step 4: Apply pagination
        stmt = stmt.offset(page * limit).limit(limit)
        result = await session.execute(stmt)
        sample_items = result.scalars().all()

        # Step 5: Return the total count and the list of sample items
        return {
            "message": "Sample items retrieved successfully.",
            "results": total,
            "data": [
                SampleItemRead.model_validate(sample_item).model_dump()
                for sample_item in sample_items
            ],
        }


@api_controller()
async def get_sample_item(sample_item_id: str) -> dict:
    """
    Retrieves a single sample item by its unique ID.

    Steps:
    1. Execute a query to fetch the sample item with the specified ID.
    2. Check if the sample item exists. If not, raise a NotFoundException.
    3. Return the sample item's details as a dictionary.

    :param sample_item_id: Unique identifier of the sample item to retrieve.
    :type sample_item_id: str
    :raises NotFoundException: If the sample item with the given ID is not found.
    :return: The requested sample item's details.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Fetch sample item by ID
        sample_item = await session.get(SampleItem, sample_item_id)

        # Step 2: If sample item not found, raise exception
        if not sample_item:
            raise NotFoundException(f"Sample item with ID '{sample_item_id}' not found")
    # Step 3: Return sample item details
    return {
        "message": f"Sample item '{sample_item.sample_item_name}' retrieved successfully.",
        "data": SampleItemRead.model_validate(sample_item).model_dump(),
    }


@api_controller(
    success_reload_events=[
        ("sample_batch_reload", "affected_sample_batch_ids"),
    ],
)
async def create_sample_items(
    sample_items: list[SampleItemCreate], independent_transaction: bool = False
) -> dict:
    """
    Creates multiple sample items in bulk after verifying associated sample files exist.

    Steps:
    1. Validate all sample files exist.
    2. Process each sample item and conditionally compute missing TIC, t0, t1 fields.
    3. Bulk create new sample items.
    4. Fetch created sample items for response and affected sample batches.
    5. Return the created sample item's details.

    :param sample_items: List of sample item details for bulk creation
    :type sample_items: list[SampleItemCreate]
    :param independent_transaction: Flag for independent transaction, defaults to False.
    :type independent_transaction: bool, optional
    :return: Details of created sample items
    :rtype: dict
    :raises NotFoundException: If any associated sample file does not exist
    """
    if not sample_items:
        return {
            "message": "No sample items to create.",
            "results": 0,
            "data": [],
        }
    async with async_session() as session:
        # Step 1: Verify all sample files exist
        sample_filenames = {si.filename for si in sample_items}
        existing_filenames = set(
            (
                await session.execute(
                    select(SampleFile.filename).where(
                        SampleFile.filename.in_(sample_filenames)
                    )
                )
            ).scalars()
        )

        if missing_files := list(sample_filenames - existing_filenames):
            raise NotFoundException(f"Sample files not found: {missing_files}")

        # Step 2: Process each sample item and conditionally compute missing TIC, t0, t1 fields
        sample_items_data = []
        for sample_item in sample_items:
            # Determine if TIC computation is needed
            tic_computation_needed = (
                sample_item.tic is None
                or sample_item.t0 is None
                or sample_item.t1 is None
            )
            # Compute TIC data if needed
            computed_tic = computed_t0 = computed_t1 = None
            if tic_computation_needed:
                try:
                    tic_time, tic_values = m_compute.get_tic_per_scan(
                        base_filename=sample_item.filename,
                        polarity=sample_item.polarity,
                    )
                    computed_tic = float(np.sum(tic_values))
                    computed_t0 = float(tic_time[0])
                    computed_t1 = float(tic_time[-1])
                except TypeError as e:
                    verbose_polarity = (
                        "positive" if sample_item.polarity == "+" else "negative"
                    )
                    raise NotFoundException(
                        f"No scans with '{verbose_polarity}' polarity were found "
                        f"in the file '{sample_item.filename}'."
                    ) from e

            sample_item_dict = {
                "sample_item_id": gen_id(),
                **sample_item.model_dump(),
                "tic": sample_item.tic if sample_item.tic is not None else computed_tic,
                "t0": sample_item.t0 if sample_item.t0 is not None else computed_t0,
                "t1": sample_item.t1 if sample_item.t1 is not None else computed_t1,
                "locked": (
                    1
                    if sample_item.sample_item_type == "ACQUISITION"
                    and sample_item_config.ACQUISITION_AUTO_LOCK
                    else 0
                ),
                "sample_item_utc_created": datetime.now(timezone.utc),
            }

            sample_items_data.append(sample_item_dict)

        # Step 3: Bulk insert using raw SQL to avoid event listeners
        await session.execute(insert(SampleItem).values(sample_items_data))
        await session.commit()

    # Step 4: Fetch created sample items for response and affected sample batches
    _, affected_sample_batch_ids, created_sample_items, _ = (
        await fetch_affected_sample_data(
            sample_item_ids=[si["sample_item_id"] for si in sample_items_data],
            include_objects=True,
        )
    )

    message = f"Successfully created {len(created_sample_items)} sample items."
    runtime.logger.debug(message)
    return {
        "message": message,
        "results": len(created_sample_items),
        "data": [
            SampleItemRead.model_validate(si).model_dump()
            for si in created_sample_items
        ],
        "_notification_data": {"affected_sample_batch_ids": affected_sample_batch_ids},
    }


@api_controller()
async def update_sample_item(
    sample_item_id: str,
    sample_item: SampleItemUpdate,
    instrument_config: SetInstrumentConfigBody | None = None,
    background_tasks: BackgroundTasks | None = None,
    independent_transaction: bool = False,
    sid: str | None = None,
    process_id: str | None = None,
) -> dict:
    """
    Updates an existing sample item with new data provided in the sample item update request body.

    Steps:
    1. Fetch the existing sample item by its ID from the database.
    2. If the sample item is found, update its properties with the new data provided.
    3. Set the sample item's modification timestamp to the current UTC time.
    4. Commit the updated sample item to the database.
    5. Process instrument configs for the sample item if needed.
    6. Reload of sample batch happens in the end of update operation if only basic fields were updated,
        or in the end of potential process_instrument_config.

    :param sample_item_id: The unique identifier of the sample item to update.
    :type sample_item_id: str
    :param sample_item: The new data for the sample item update.
    :type sample_item: SampleItemUpdate
    :param instrument_config: Optional instrument configuration to process.
    :type instrument_config: SetInstrumentConfigBody | None
    :param background_tasks: FastAPI background tasks for processing instrument config post-update.
    :type background_tasks: BackgroundTasks | None
    :param independent_transaction: Flag to indicate if the operation should be treated as an independent transaction.
    :type independent_transaction: bool
    :param sid: Socket.IO session ID, used for emitting notifications to specific clients.
    :type sid: str | None
    :param process_id: Process identifier for tracking background operations.
    :type process_id: str | None
    :raises NotFoundException: If no sample item is found with the provided ID.
    :return: The updated sample item data as a dictionary.
    :rtype: dict[str, Any]
    """
    # verify instrument config exists
    if instrument_config and instrument_config.instrument_function_id is not None:
        await get_instrument_config(
            instrument_function_id=instrument_config.instrument_function_id
        )

    # Step 1: Fetch the existing sample item
    async with async_session() as session:
        existing_sample_item = await session.get(SampleItem, sample_item_id)
        if not existing_sample_item:
            raise NotFoundException(f"Sample item with ID '{sample_item_id}' not found")

        # Step 2: Update the sample item properties if anything changed
        update_data = sample_item.model_dump(exclude_unset=True)
        changed_fields = {
            key: value
            for key, value in update_data.items()
            if getattr(existing_sample_item, key) != value
        }
        if changed_fields:
            # Update only the changed fields
            for key, value in changed_fields.items():
                setattr(existing_sample_item, key, value)

            # Step 3: Update modification timestamp
            existing_sample_item.sample_item_utc_modified = datetime.now(timezone.utc)

            # Step 4: Commit the updates
            await session.commit()
            await session.refresh(existing_sample_item)

    # Step 5: Process instrument config
    sample = await fetch_sample(sample_item_id)
    current_instrument_id = getattr(sample, "instrument_function_id", None)

    # Process only if there's a new record or the instrument_function_id changed
    if instrument_config is not None and (
        instrument_config.new_record
        or instrument_config.instrument_function_id != current_instrument_id
    ):
        background_tasks.add_task(
            process_instrument_config,
            filenames=[existing_sample_item.filename],
            instrument_config=instrument_config,
            independent_transaction=True,
            sid=sid,
            process_id=process_id,
        )
    # Step 6: Directly reload batch if needed # TODO_invalidation
    elif changed_fields:
        await sio.emit(
            "sample_batch_reload",
            room=existing_sample_item.sample_batch_id,
            namespace="/",
        )

    return {
        "message": f"Sample '{existing_sample_item.sample_item_name}' was updated.",
        "data": SampleItemRead.model_validate(existing_sample_item).model_dump(),
    }


@api_controller(
    success_reload_events=[
        ("sample_batch_reload", "affected_sample_batch_ids"),
    ],  # TODO_invalidation
)
async def delete_sample_items(
    sample_item_ids: list[str], independent_transaction: bool = False
):
    """
    Deletes a sample item by its unique identifier.

    Steps:
    1. Check no duplicate sample item ids were provided
    2. Check sample items to be deleted exist
    3. Retrieve affected batch ids
    4. Delete samples

    :param sample_item_id: The unique identifier of the sample item to delete.
    :type sample_item_id: str
    :raises NotFoundException: If no sample item is found with the provided ID.
    """
    # Step 1: Check no duplicate sample item ids were provided
    if len(set(sample_item_ids)) < len(sample_item_ids):
        raise ValueError("delete sample items: sample item IDs must be unique")
    async with async_session() as session:
        # Step 2: Check sample items to delete exist
        result = await session.execute(
            select(SampleItem).where(SampleItem.sample_item_id.in_(sample_item_ids))
        )
        sample_items = result.scalars().all()
        if missing_ids := list(
            set(sample_item_ids) - {s.sample_item_id for s in sample_items}
        ):
            s = "s" if len(missing_ids) > 1 else ""
            raise NotFoundException(
                f"Failed to find {len(missing_ids)} sample item{s}: {missing_ids}"
            )
        # Step 3: Retrieve affected batch ids
        _, affected_sample_batch_ids, *_ = await fetch_affected_sample_data(
            sample_item_ids=sample_item_ids
        )
        # Step 4: Delete the sample items
        delete_query = delete(SampleItem).where(
            SampleItem.sample_item_id.in_(sample_item_ids)
        )
        await session.execute(delete_query)
        await session.commit()

    s = "s" if len(sample_item_ids) > 1 else ""
    return {
        "message": f"Deleted {len(sample_item_ids)} sample item{s}.",
        "_notification_data": {"affected_sample_batch_ids": affected_sample_batch_ids},
    }


@api_controller_background_task(
    success_notification_rooms=["sid"],
    success_reload=[("sample_batch_reload", "sample_batch_id")],
    error_notification_rooms=["sid"],
)
async def copy_sample_items(
    sample_item_ids: list[str],
    sample_batch_id: str,
    always_copy_matches: bool = False,
    independent_transaction: bool = False,
    background_tasks: BackgroundTasks = None,
    sid=None,
    process_id=None,
    parent_id=None,
) -> dict:
    """
    TODO_api_circular_import  distinguish sample and sample_item controller, should be moved to samples_controller.py?
    The function copies the specified sample item and associates the new copy with a specified sample batch.
    May be a part of the copy sample batch operation or independent.
    Copies matches, match interferences of the original sample if part of a larger copy batch operation
    or if it is copied to the same batch, since targets and ionization mechanisms are the same for original batch and new batch.
    Computes matches if it's an independent operation and target and original batch differ,
    since the targets and ionization mechanisms may differ between original batch and new batch.


    Steps:
    1. Validate the batch into which the samples are copied
    2. Fetch and validate the original sample items from the database.
    3. Create and add to session a new sample items with updated information.
    4. Copy match data if necessary.
    5. Commit the transaction to the database.
    6. Compute matches if necessary.

    :param sample_item_ids: ID of the original sample items to be copied.
    :type sample_item_ids: list[str]
    :param sample_batch_id: ID of the sample batch where the new items will be placed.
    :type sample_batch_id: str
    :param always_copy_matches: Whether to copy matches even when copying between different batches (used in batch copy controller)
    :type always_copy_matches: bool
    :param independent_transaction: Flag indicating whether the sample item copy is an independent transaction and if the operation should emit a reload event for the sample batch and if the sample should be rematched for new batch targets, defaults to False
    :type independent_transaction: bool, optional
    :param background_tasks: FastAPI background tasks for computing matches post-copy, defaults to None
    :type background_tasks: BackgroundTasks, optional
    :param sid: Session ID, used for emitting notifications to specific clients, defaults to None
    :type sid: str, optional
    :raises NotFoundException: If the original sample item is not found.
    :return: The newly created sample item dict.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Validate the batch into which the sample is being copied.
        if not (sample_batch := await session.get(SampleBatch, sample_batch_id)):
            raise NotFoundException(
                f"Sample batch with ID '{sample_batch_id}' not found"
            )

        if len(set(sample_item_ids)) < len(sample_item_ids):
            raise ValueError("sample_item_ids to be copied must be unique")

        # Step 2: Fetch and validate the original sample items
        result = await session.execute(
            select(SampleItem).where(SampleItem.sample_item_id.in_(sample_item_ids))
        )
        original_sample_items = result.scalars().all()

        if missing_ids := set(sample_item_ids) - {
            si.sample_item_id for si in original_sample_items
        }:
            raise NotFoundException(f"Sample items not found: {list(missing_ids)}")

    # Step 3: Prepare SampleItemCreate objects with copy transformations
    sample_items_to_create = []
    for original in original_sample_items:
        sample_item_create = SampleItemCreate(
            **SampleItemBase.model_validate(original).model_dump(
                exclude={"sample_batch_id", "sample_item_name", "sample_item_type"}
            ),
            sample_batch_id=sample_batch_id,
            sample_item_name=(
                generate_copy_name(original.sample_item_name)
                if original.sample_batch_id == sample_batch_id
                else original.sample_item_name
            ),
            sample_item_type=(
                "UNKNOWN"
                if original.sample_item_type == "ACQUISITION"
                else original.sample_item_type
            ),
        )

        sample_items_to_create.append(sample_item_create)

    # Step 4: Bulk create sample items
    creation_result = await create_sample_items(
        sample_items=sample_items_to_create,
        independent_transaction=False,
    )

    created_items_data = creation_result["data"]

    # Step 4: Prepare match operations using zip for cleaner iteration
    sample_match_copies = []
    samples_to_rematch_ids = []

    for original, created_item in zip(original_sample_items, created_items_data):
        new_item_id = created_item["sample_item_id"]

        if original.sample_batch_id == sample_batch_id or always_copy_matches:
            sample_match_copies.append(
                CopyMatches(original.sample_item_id, new_item_id)
            )
        else:
            samples_to_rematch_ids.append(new_item_id)

    # Step 5: Copy match records if necessary
    if sample_match_copies:
        notification = UserNotification(
            process_id=process_id,
            parent_id=parent_id,
            type="copy_sample_items",
            status="pending",
            message=f"Copying match records for {len(sample_item_ids)} samples.",
            data={
                "sample_match_copies": [copy._asdict() for copy in sample_match_copies],
                "sample_batch_id": sample_batch_id,
                "_room_ids": [sid],
                "_sid": sid,
            },
        )
        await copy_sample_items_match_data(
            sample_match_copies,
            notification,
        )

    # Step 6: Compute matches if necessary for copied samples
    # (not the whole target batch, since it may be not empty)
    if samples_to_rematch_ids:
        background_tasks.add_task(
            match_compute_samples,
            sample_item_ids=samples_to_rematch_ids,
            added_target_compound_ids=None,
            added_ionization_mechanism_ids=None,
            independent_transaction=True,  # TODO_invalidation - reload each sample when it is computed
            sid=sid,
            process_id=gen_id(8),
            parent_id=process_id,
        )

    # Step 7: Return the copied sample and message
    return {
        "message": f"Copied {len(created_items_data)} samples successfully to batch '{sample_batch.sample_batch_name}'.",
        "data": created_items_data,
        "_notification_data": {
            "affected_sample_item_ids": [
                si["sample_item_id"] for si in created_items_data
            ],
        },
    }


@api_controller_background_task(
    success_notification_rooms=["sid"],
    success_reload=[("sample_batch_reload", "affected_sample_batch_ids")],
    error_notification_rooms=["sid"],
)
async def move_sample_items(
    sample_item_ids: list[str],
    sample_batch_id: str,
    independent_transaction: bool = False,
    background_tasks: BackgroundTasks = None,
    sid=None,
    process_id=None,
    parent_id=None,
) -> dict:
    """
    Move a set of samples to a specific batch. Leverages the copy_sample_items
    and delete_sample_items controllers:

    Steps:
    1. Validate batch existence
    2. Validate samples existence
    3. Validate move is between different batches
    4. Copy sample items over to the batch
    5. Delete the original sample items if successful

    :param sample_item_ids: ID of the original sample items to be moved.
    :type sample_item_ids: list[str[]
    :param sample_batch_id: ID of the sample batch where the items will be placed.
    :type sample_batch_id: str
    :param independent_transaction: Flag indicating whether the sample item copy is an independent transaction and if the operation should emit a reload event for the sample batch and if the sample should be rematched for new batch targets, defaults to False
    :type independent_transaction: bool, optional
    :param background_tasks: FastAPI background tasks for computing matches post-copy, defaults to None
    :type background_tasks: BackgroundTasks, optional
    :param sid: Session ID, used for emitting notifications to specific clients, defaults to None
    :type sid: str, optional
    :raises NotFoundException: If the original sample item is not found.
    :return: The newly created sample item dict.
    :rtype: dict
    """

    # Step 1. Validate batch existence
    async with async_session() as session:
        batch = await session.get(SampleBatch, sample_batch_id)

        if not batch:
            raise NotFoundException(
                f"Sample batch with ID '{sample_batch_id}' not found"
            )

        # Step 2. Validate samples existence
        stmt = select(SampleItem).where(SampleItem.sample_item_id.in_(sample_item_ids))
        result = await session.execute(stmt)
        original_samples = result.scalars().all()
        original_sample_item_ids = [
            original.sample_item_id for original in original_samples
        ]

        missing_sample_item_ids = [
            id for id in sample_item_ids if id not in original_sample_item_ids
        ]
        for missing_sample_item_id in missing_sample_item_ids:
            raise NotFoundException(
                f"Sample item with ID '{missing_sample_item_id}' not found"
            )

    # Step 3. Validate move is between different batches
    _, affected_sample_batch_ids, *_ = await fetch_affected_sample_data(
        sample_item_ids=sample_item_ids
    )
    if sample_batch_id in affected_sample_batch_ids:
        raise ValueError(
            "Move sample items: some of the samples you are trying to move are already in the requested batch"
        )

    # Step 4: copy sample items over
    copy_result = await copy_sample_items(
        sample_item_ids=sample_item_ids,
        sample_batch_id=sample_batch_id,
        independent_transaction=False,
        background_tasks=background_tasks,
        sid=sid,
        process_id=gen_id(8),
        parent_id=process_id,
    )
    moved_samples = copy_result["data"]

    # Step 5. Delete original samples if copy successful
    if moved_samples:
        await delete_sample_items(
            sample_item_ids=sample_item_ids,
        )
    return {
        "message": f"Moved {len(sample_item_ids)} samples successfully to batch '{batch.sample_batch_name}'.",
        "data": moved_samples,
        "_notification_data": {
            "affected_sample_item_ids": sample_item_ids,
            "affected_sample_batch_ids": [sample_batch_id, *affected_sample_batch_ids],
        },
    }


@api_controller_background_task(
    success_notification_rooms=["sid"],
    error_notification_rooms=["sid"],
)
async def sample_item_export_peaks(
    sample_item_id: str,
    independent_transaction: bool = False,
    sid=None,
    process_id=None,
    parent_id=None,
):
    """Exports peak data for a specific sample item to a CSV file. This process involves loading sample file
    as a sample view, detecting peaks, and compiling peak data into a DataFrame before saving it to a file.

    Peak data is exported as a CSV file with the following columns:
    - datetime: The date and time of the scan in the local timezone.
    - datetime_utc: The date and time of the scan in UTC.
    - tic: The total ion current for the scan.
    - mz: The mass-to-charge ratio of the peak.
    - intensity: The intensity of the peak in each scan.
    - unit: The unit of the intensity value (ions for TOF or relative for Orbitrap).
    - sample_batch_name: The name of the sample batch.
    - sample_item_name: The name of the sample item.
    - filename: The filename of the sample file.
    - filter_id: The ID of the filter used.
    - sample_item_type: The type of the sample item.
    - sample_file_id: The ID of the sample file.
    - sample_item_id: The ID of the sample item.
    - instrument: The type of the instrument used for the sample file.

    :param sample_item_id: ID of the sample item.
    :type sample_item_id: str
    :param independent_transaction: Flag to indicate if the operation should be treated as an independent transaction, defaults to False.
    :type independent_transaction: bool, optional
    :param sid: Session ID for targeting specific clients when emitting events, defaults to None.
    :type sid: str, optional
    """
    # Get sample item data as a sample view
    sample_result = await get_sample(sample_item_id)
    sample = sample_result.get("data")
    sample_item_name = sample["sample_item_name"]

    # Get sample batch name
    sample_batch_id = sample["sample_batch_id"]
    sample_batch_data = await fetch_sample_batch_data(sample_batch_id)
    sample_batch_name = sample_batch_data.sample_batch_name

    # Prepare notification
    notification = UserNotification(
        process_id=process_id,
        parent_id=parent_id,
        type="sample_item_export_peaks",
        status="pending",
        message=f"Exporting peak data for sample item '{sample_item_name}'",
        # NOTE set the internal room_ids for the pending user_notifications and sid of the user, will be removed from the data.
        data={
            "sample_item_id": sample_item_id,
            "sample_batch_id": sample_batch_id,
            "_room_ids": [sid],
            "_sid": sid,
        },
    )

    await send_progress_user_notification(notification, 0.1)

    try:
        filename = sample["filename"]
        instrument_functions = await read_instrument_functions(filename=filename)
        instrument_type = get_instrument_type(filename)

        await send_progress_user_notification(notification, 0.1)

        # Assign peak fitting threshold and peak abundance units
        # depending on the instrument type
        # Correct intrument type unsured by get_instrument_type
        if instrument_type == "orbi":
            threshold = ORBI_FITTING_THRESHOLD
            peak_data_type = "peak_heights"
        if instrument_type == "tof":
            threshold = TOF_FITTING_THRESHOLD
            peak_data_type = "peak_areas"
        sample_file = await detect_peaks(
            filename,
            instrument_functions,
            threshold,
            u_list=None,
            if_exists="append",
            instrument_type=instrument_type,
        )

        sample_peak_data = sample_file[peak_data_type].dropna(dim="mz", how="all")

        await send_progress_user_notification(notification, 0.8)
    except Exception as e:
        runtime.logger.error(repr(e))
        raise e

    # File creation timestamp
    base_datetime = sample["datetime"]
    # Get sample peak timestamps local
    sample_peak_time = sample_peak_data.time.values
    # Convert peak time to timedelta
    sample_peak_timedelta = pd.to_timedelta(sample_peak_time, unit="s")
    # Get scan timestamps relative to the base datetime
    scan_timestamps = sample_peak_timedelta + pd.Timestamp(base_datetime)
    # Get scan timestamps UTC
    base_datetime_utc = sample["datetime_utc"]
    scan_timestamps_utc = sample_peak_timedelta + pd.Timestamp(base_datetime_utc)
    # Get ticks for each time scan
    _, scan_tics = m_compute.get_tic_per_scan(filename)

    mz_values = sample_peak_data.mz.values
    intensities = sample_peak_data.values

    # Create arrays for the repeated values
    repeated_datetimes = np.repeat(
        scan_timestamps.values[:, np.newaxis], len(mz_values), axis=1
    )
    repeated_datetimes_utc = np.repeat(
        scan_timestamps_utc.values[:, np.newaxis], len(mz_values), axis=1
    )
    repeated_tics = np.repeat(scan_tics[:, np.newaxis], len(mz_values), axis=1)
    repeated_mz = np.repeat(mz_values, len(scan_timestamps))

    # Create the final DataFrame
    sample_peak_df = pd.DataFrame(
        {
            "datetime": repeated_datetimes.T.flatten(),
            "datetime_utc": repeated_datetimes_utc.T.flatten(),
            "tic": repeated_tics.T.flatten(),
            "mz": repeated_mz.flatten(),
            "intensity": intensities.flatten(),
        }
    ).assign(
        unit="ions" if instrument_type == "tof" else "counts",
        sample_batch_name=sample_batch_name,
        sample_item_name=sample_item_name,
        filename=filename,
        filter_id=sample["filter_id"],
        sample_item_type=sample["sample_item_type"],
        sample_file_id=sample["sample_file_id"],
        sample_item_id=sample["sample_item_id"],
        instrument=sample["instrument"],
    )

    await send_progress_user_notification(notification, 1)

    # Get the current date and time as a string for a filename
    dt_str = datetime.now().isoformat().replace("-", "").replace(":", "").split(".")[0]

    # Save the peak data to a CSV file
    peakfile_filename = "_".join(
        [dt_str, "peak_data", sample_item_name.replace(" ", "_") + ".csv"]
    )
    runtime.logger.info(f"Writing peak data to file {peakfile_filename}")
    sample_peak_df.to_csv(
        runtime.env.path("temp", peakfile_filename), index=False, sep=";"
    )
    message = f"Peak data for sample item '{sample_item_name}' was exported to file '{peakfile_filename}'."
    runtime.logger.info(message)

    # Return the status message
    return {
        "message": message,
        "data": {"filename": peakfile_filename},
        "_notification_data": {
            "sample_item_id": sample_item_id,
            "download": peakfile_filename,
        },
    }
