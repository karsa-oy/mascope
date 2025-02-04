from datetime import datetime, timezone
from fastapi import BackgroundTasks
from sqlalchemy import (
    select,
    asc,
    desc,
    func,
)
from mascope_server.socket import sio
from mascope_server.db import async_session
from mascope_server.db.id import gen_id
from mascope_server.db.models import (
    SampleBatch,
    SampleItem,
    SampleFile,
)
from mascope_server.api.lib.api_features import (
    api_controller,
    api_controller_background_task,
)
from mascope_server.api.lib.exceptions.api_exceptions import (
    NotFoundException,
)
from mascope_server.api.controllers.sample.lib.sample_items_copy import (
    copy_sample_item_match_data,
)
from mascope_server.api.controllers.match.match_controller import match_compute_sample
from mascope_server.api.models.sample.items.sample_item_pydantic_model import (
    SampleItemCreate,
    SampleItemUpdate,
)
from mascope_server.socket.notifications import (
    UserNotification,
)
from mascope_server.api.new.instrument_configs.service import get_instrument_config
from mascope_server.api.new.instrument_configs.schemas import (
    SetInstrumentConfigBody,
)
from mascope_server.api.new.instrument_configs.process.service import (
    process_instrument_config,
)


@api_controller()
async def get_sample_items(
    sample_batch_id: str = None,
    filename: str = None,
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
            "data": [sample_item.to_dict() for sample_item in sample_items],
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
        "data": sample_item.to_dict(),
    }


@api_controller(
    emit_reload_events=[
        ("sample_batch_reload", "sample_batch_id"),
    ],
)
async def create_sample_item(
    sample_item: SampleItemCreate, independent_transaction: bool = False
) -> dict:
    """
    Creates a new sample item with the specified details after verifying that an associated
    sample file exists in the database.

    Steps:
    1. Verify that the sample file with the given filename exists in the database.
    2. Create a new sample item object with the provided details and a generated ID.
    3. Add the new sample item to the session and commit the changes to the database.
    4. Return the details of the created sample item.

    :param sample_item: Sample item creation details from the request body.
    :type sample_item: SampleItemCreate
    :param independent_transaction: Flag indicating whether the sample item create is an independent transaction, defaults to False
    :type independent_transaction: bool, optional
    :return: The created sample item's details.
    :rtype: dict
    :raises NotFoundException: Raised if the associated sample file does not exist.
    """
    async with async_session() as session:
        # Step 1: Verify the existence of the sample file
        result = await session.execute(
            select(SampleFile).where(SampleFile.filename == sample_item.filename)
        )
        sample_file = result.scalars().one_or_none()

        if not sample_file:
            raise NotFoundException(
                f"Sample file with filename '{sample_item.filename}' not found"
            )
        # Step 2: Generate unique ID and create new sample item
        new_sample_item = SampleItem(
            sample_item_id=gen_id(),
            **sample_item.model_dump(),  # Pydantic model's data
            sample_item_utc_created=datetime.now(timezone.utc),
            sample_item_utc_modified=datetime.now(timezone.utc),
        )
        # Step 3: Add to session and commit
        session.add(new_sample_item)
        await session.commit()
        await session.refresh(new_sample_item)

    # Step 4: Return the new sample item details
    return {
        "message": f"Sample item '{new_sample_item.sample_item_name}' was created.",
        "data": new_sample_item.to_dict(),
    }


@api_controller()
async def update_sample_item(
    sample_item_id: str,
    sample_item: SampleItemUpdate,
    instrument_config: SetInstrumentConfigBody | None = None,
    background_tasks: BackgroundTasks | None = None,
    sid=None,
    process_id=None,
) -> dict:
    """
    Updates an existing sample item with new data provided in the sample item update request body.

    Steps:
    1. Fetch the existing sample item by its ID from the database.
    2. If the sample item is found, update its properties with the new data provided.
    3. Set the sample item's modification timestamp to the current UTC time.
    4. Commit the updated sample item to the database.
    5. Process instrument configs for the sample item if needed.
    6. Reload the sample batch if needed.

    :param sample_item_id: The unique identifier of the sample item to update.
    :type sample_item_id: str
    :param sample_item: The new data for the sample item update.
    :type sample_item: sample itemUpdate
    :raises NotFoundException: If no sample item is found with the provided ID.
    :return: The updated sample item data as a dictionary.
    :rtype: dict

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

        # Step 2: Update the sample item properties
        update_data = sample_item.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(existing_sample_item, key, value)

        # Step 3: Update modification timestamp
        existing_sample_item.sample_item_utc_modified = datetime.now(timezone.utc)

        # Step 4: Commit the updates
        await session.commit()
        await session.refresh(existing_sample_item)

    # Step 5: Process instrument config
    if instrument_config:
        background_tasks.add_task(
            process_instrument_config,
            filenames=[existing_sample_item.filename],
            instrument_config=instrument_config,
            independent_transaction=True,
            sid=sid,
            process_id=process_id,
        )
    else:
        # Step 6: Reload batch if needed
        await sio.emit(
            "sample_batch_reload",
            room=existing_sample_item.sample_batch_id,
            namespace="/",
        )
        # TODO_invalidation
    return {
        "message": f"Sample '{existing_sample_item.sample_item_name}' was updated.",
        "data": existing_sample_item.to_dict(),
    }


@api_controller()
async def delete_sample_item(sample_item_id: str):
    """
    Deletes a sample item by its unique identifier.

    Steps:
    1. Fetch the sample item by its ID from the database.
    2. If the sample item is found, delete it from the session and commit the changes to the database.
    3. Emit socket.io events to inform clients about the sample item deletion.

    :param sample_item_id: The unique identifier of the sample item to delete.
    :type sample_item_id: str
    :raises NotFoundException: If no sample item is found with the provided ID.
    """
    # Step 1: Fetch the sample item
    async with async_session() as session:
        sample_item = await session.get(SampleItem, sample_item_id)
        if not sample_item:
            raise NotFoundException(f"Sample item with ID '{sample_item_id}' not found")
        # Step 2: Delete the sample item and commit changes
        await session.delete(sample_item)
        await session.commit()
    # Step 3: Emit socket.io events
    await sio.emit(
        "sample_batch_reload",
        room=sample_item.sample_batch_id,
        namespace="/",
    )

    return {
        "message": f"Sample item '{sample_item.sample_item_name}' was deleted.",
    }


@api_controller_background_task(
    success_notification_rooms=["sid"],
    success_reload=[("sample_batch_reload", "sample_batch_id")],
    error_notification_rooms=["sid"],
)
async def copy_sample_item(
    sample_item_id: str,
    sample_batch_id: str,
    sample_item_name: str,
    independent_transaction: bool = False,
    background_tasks: BackgroundTasks = None,
    sid=None,
    process_id=None,
    parent_id=None,
) -> dict:
    """
    TODO_api_circular_import  destinguish sample and sample_item controller, should be mocveved to samples_controller.py?
    The function copies the specified sample item and associates the new copy with a specified sample batch.
    May be a part of the copy sample batch operation or independent.
    Copies matches, match interferences of the original sample if part of a larger copy batch operation
    or if it is copied to the same batch, since targets and ionization mechanisms are the same for original batch and new batch.
    Computes matches if it's an independent operation and target and original batch differ,
    since the targets and ionization mechanisms may differ between original batch and new batch.


    Steps:
    1. Validate the batch into which the sample is being copied.
    2. Fetch and validate the original sample item from the database.
    3. Create and add to session a new sample item with updated information.
    4. Copy matches and match interferences if copying to the same batch or as part of a larger copy batch operation.
    5. Commit the transaction to the database.
    6. If an independent operation, compute matches due to target changes.

    :param sample_item_id: ID of the original sample item to be copied.
    :type sample_item_id: str
    :param sample_batch_id: ID of the sample batch where the new item will be placed.
    :type sample_batch_id: str
    :param sample_item_name: Name for the new copied sample item.
    :type sample_item_name: str
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
        batch = await session.get(SampleBatch, sample_batch_id)

        if not batch:
            raise NotFoundException(
                f"Sample batch with ID '{sample_batch_id}' not found"
            )

        # Step 2: Fetch and validate the original sample item along with related match records
        stmt = select(SampleItem).filter(SampleItem.sample_item_id == sample_item_id)
        result = await session.execute(stmt)
        original_sample_item = result.scalars().first()

        if not original_sample_item:
            raise NotFoundException(f"Sample item with ID '{sample_item_id}' not found")

        # Step 3: Create and add to session the new sample item with a new ID, name, batch and time of creation, but copy all other data
        new_sample_item_id = gen_id()
        new_sample_item_data = {
            c.name: getattr(original_sample_item, c.name)
            for c in SampleItem.__table__.columns
            if c.name != "sample_item_id"
        }
        new_sample_item_data.update(
            {
                "sample_item_id": new_sample_item_id,
                "sample_batch_id": sample_batch_id,
                "sample_item_name": sample_item_name,
                "sample_item_utc_created": datetime.now(timezone.utc),
            }
        )
        new_sample_item = SampleItem(**new_sample_item_data)
        session.add(new_sample_item)

        # Steps 4: Copy match records when called as part of copy_sample_batch or if sample is copied within the same batch
        if (
            not independent_transaction
            or original_sample_item.sample_batch_id == sample_batch_id
        ):
            # Prepare progress user notification for match copying
            notification = UserNotification(
                process_id=process_id,
                parent_id=parent_id,
                type="copy_sample_item",
                status="pending",
                message=f"Copying match records for sample '{sample_item_name}'.",
                data={
                    "sample_item_id": new_sample_item_id,
                    "sample_batch_id": sample_batch_id,
                    "_room_ids": [sid],
                    "_sid": sid,
                },
            )

            await copy_sample_item_match_data(
                original_sample_item.sample_item_id,
                new_sample_item_id,
                session,
                notification,
            )

        # Step 5: Commit the transaction
        await session.commit()
        await session.refresh(new_sample_item)

    # Step 6: Create task to compute the sample match data when called independently and not withing the same batch.
    if (
        independent_transaction
        and original_sample_item.sample_batch_id != sample_batch_id
    ):
        background_tasks.add_task(
            match_compute_sample,
            sample_item_id=new_sample_item_id,
            added_target_compound_ids=None,
            added_ionization_mechanism_ids=None,
            independent_transaction=independent_transaction,
            sid=sid,
            process_id=process_id,
        )

    # Step 7: Return the copied samle and message
    return {
        "message": f"Sample '{new_sample_item.sample_item_name}' was successfully copied to sample batch '{batch.sample_batch_name}'.",
        "data": new_sample_item.to_dict(),
        "_notification_data": {
            "sample_item_id": new_sample_item_id,
            "sample_batch_id": sample_batch_id,
        },
    }
