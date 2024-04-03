from fastapi import BackgroundTasks
from sqlalchemy import asc, desc, func
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from datetime import datetime, timezone

from backend.server import sio
from backend.db.id import gen_id
from backend.db_api_rest import async_session
from ..utils.api_features import api_controller, api_controller_background_task
from ..exceptions import NotFoundException
from ..controllers.match_controller import match_sample_compute
from ..models.models import (
    SampleItem,
    SampleBatch,
    Match,
    MatchInterference,
)
from ..models.pydantic_models.sample_item_pydantic_model import (
    SampleItemCreate,
    SampleItemUpdate,
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
        count_stmt = select(func.count()).select_from(stmt)
        total = await session.scalar(count_stmt)

        # Step 4: Apply pagination
        stmt = stmt.offset(page * limit).limit(limit)
        result = await session.execute(stmt)
        sample_items = result.scalars().all()

        # Step 5: Return the total count and the list of sample items
        return {
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
    return sample_item.to_dict()


@api_controller()
async def create_sample_item(
    sample_item: SampleItemCreate, independent_transaction: bool = False
) -> dict:
    """
    Creates a new sample item with the specified details.

    Steps:
    1. Create a new sample item object with the provided details and the generated ID.
    2. Add the new sample item to the session and commit the changes to the database.
    3. Emit a signal to inform clients about the creation of the new sample item.
    4. Return the details of the created sample item.

    :param sample_item: Sample item creation details from the request body.
    :type sample_item: SampleItemCreate
    :param independent_transaction: Flag indicating whether the sample item create is an independent transaction, defaults to False
    :type independent_transaction: bool, optional
    :return: The created sample item's details.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Generate unique ID and create new sample item
        new_sample_item = SampleItem(
            sample_item_id=gen_id(),
            **sample_item.dict(),  # Pydantic model's data
            sample_item_utc_created=datetime.now(timezone.utc),
            sample_item_utc_modified=datetime.now(timezone.utc),
        )
        # Step 2: Add to session and commit
        session.add(new_sample_item)
        await session.commit()
        await session.refresh(new_sample_item)

    # Step 3: Emit event
    # TODO_notifications refactor onSampleItemCreated
    if independent_transaction:
        await sio.emit(
            "sample_item_created",
            new_sample_item.sample_item_id,
            room=new_sample_item.sample_batch_id,
            namespace="/",
        )
    # Step 4: Return the new sample item details
    return new_sample_item.to_dict()


@api_controller()
async def update_sample_item(
    sample_item_id: str, sample_item: SampleItemUpdate
) -> dict:
    """
    Updates an existing sample item with new data provided in the sample item update request body.

    Steps:
    1. Fetch the existing sample item by its ID from the database.
    2. If the sample item is found, update its properties with the new data provided.
    3. Set the sample item's modification timestamp to the current UTC time.
    4. Commit the updated sample item to the database.
    5. Emit socket.io events to inform clients about the sample item update.

    :param sample_item_id: The unique identifier of the sample item to update.
    :type sample_item_id: str
    :param sample_item: The new data for the sample item update.
    :type sample_item: sample itemUpdate
    :raises NotFoundException: If no sample item is found with the provided ID.
    :return: The updated sample item data as a dictionary.
    :rtype: dict

    """
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

        # Step 5: Emit socket.io events
        await sio.emit(
            "sample_batch_reload",
            room=existing_sample_item.sample_batch_id,
            namespace="/",
        )
        return existing_sample_item.to_dict()


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


@api_controller_background_task(
    success_emit_events=[
        ("copy_finished", "sid"),
    ],
    error_emit_events=[
        ("copy_finished", "sid"),
    ],
    default_payload={
        "action": "copy",
        "type": "sample",
    },
    success_message="Sample item was successfully copied",
)
async def copy_sample_item(
    sample_item_id: str,
    sample_batch_id: str,
    sample_item_name: str,
    independent_transaction: bool = False,
    background_tasks: BackgroundTasks = None,
    sid=None,
) -> dict:
    """
    Copies a sample item to a new sample batch with a new name. May me independent operation or a part of the copy sample batch operation.
    The function duplicates the specified sample item and associates the new copy with a specified sample batch.
    Copies matches, match interferences of the original sample if part of a larger copy batch operation, since targets and ionization mechanisms are the same for original batch and new batch.
    Computes matches if it's an independent operation, since the targets and ionization mechanisms may differ between original batch and new batch.


    Steps:
    1. Validate the batch into which the sample is being copied.
    2. Fetch and validate the original sample item from the database.
    3. Create and add to session a new sample item with updated information.
    4. Copy match and match interference records when called as part of copy_sample_batch.
    5. Commit the transaction to the database.
    6. Create task to compute the sample match data when called independently.

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

        # Step 2: Fetch and validate the original sample item along with related Match and MatchInterference records
        stmt = (
            select(SampleItem)
            .options(
                joinedload(SampleItem.match),
                joinedload(SampleItem.match_interference),
            )
            .filter(SampleItem.sample_item_id == sample_item_id)
        )
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

        # Steps 4: Copy Match and MatchInterference records when called as part of copy_sample_batch
        if not independent_transaction and not background_tasks:
            # Copy related Match records
            for match in original_sample_item.match:
                new_match_data = {
                    c.name: getattr(match, c.name)
                    for c in Match.__table__.columns
                    if c.name != "match_id"
                }
                new_match_data.update(
                    {"match_id": gen_id(32), "sample_item_id": new_sample_item_id}
                )
                new_match = Match(**new_match_data)
                session.add(new_match)

            # Copy related MatchInterference records
            for match_interference in original_sample_item.match_interference:
                new_match_interference_data = {
                    c.name: getattr(match_interference, c.name)
                    for c in MatchInterference.__table__.columns
                    if c.name != "match_interference_id"
                }
                new_match_interference_data.update(
                    {
                        "match_interference_id": gen_id(32),
                        "sample_item_id": new_sample_item_id,
                    }
                )
                new_match_interference = MatchInterference(
                    **new_match_interference_data
                )
                session.add(new_match_interference)

        # Step 5: Commit the transaction
        await session.commit()
        await session.refresh(new_sample_item)

    # Step 6: Create task to compute the sample match data when called independently.
    if independent_transaction and background_tasks:
        background_tasks.add_task(
            match_sample_compute,
            sample_item_id=new_sample_item_id,
            added_target_compound_ids=None,
            added_ionization_mechanism_ids=None,
            independent_transaction=independent_transaction,
            sid=sid,
        )

    return new_sample_item.to_dict()
