from fastapi import HTTPException, status, BackgroundTasks
from sqlalchemy import asc, desc, func
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from datetime import datetime

from backend.api_sio import sio
from backend.db import async_session
from backend.db.id import gen_id

from ..models.models import (
    SampleFile,
    SampleItem,
    SampleBatch,
    Match,
    MatchInterference,
)
from ..models.pydantic_models.sample_item_pydantic_model import (
    SampleItemCreate,
    SampleItemUpdate,
)
from ..exceptions import process_exception, ApiException, NotFoundException

from ..controllers.match_controller import match_sample_compute


async def get_sample_items(
    sample_batch_id: str = None,
    filename: str = None,
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 10000,
):
    async with async_session() as session:
        stmt = select(SampleItem)

        if sample_batch_id:
            stmt = stmt.filter(SampleItem.sample_batch_id == sample_batch_id)

        if filename:
            stmt = stmt.filter(SampleItem.filename == filename)

        if sort:
            if sort == "tic":
                stmt = stmt.outerjoin(
                    SampleFile, SampleItem.filename == SampleFile.filename
                )
                if order == "desc":
                    stmt = stmt.order_by(desc(SampleFile.tic))
                else:
                    stmt = stmt.order_by(asc(SampleFile.tic))
            else:
                if order == "desc":
                    stmt = stmt.order_by(desc(getattr(SampleItem, sort)))
                else:
                    stmt = stmt.order_by(asc(getattr(SampleItem, sort)))

        # Get total count
        count_stmt = select(func.count()).select_from(stmt)
        total = await session.scalar(count_stmt)

        # Get paginated results
        stmt = stmt.offset(page * limit).limit(limit)
        result = await session.execute(stmt)
        sample_items = result.scalars().all()

        return {
            "results": total,
            "data": [sample_item.to_dict() for sample_item in sample_items],
        }


async def get_sample_item(sample_item_id: str):
    async with async_session() as session:
        stmt = select(SampleItem).filter(SampleItem.sample_item_id == sample_item_id)
        result = await session.execute(stmt)
        sample_item = result.scalars().first()

        if not sample_item:
            raise HTTPException(
                status_code=404,
                detail=f"sample_item with ID {sample_item_id} not found",
            )

        return sample_item.to_dict()


async def create_sample_item(sample_item: SampleItemCreate, skipReload: bool = False):
    async with async_session() as session:
        new_sample_item = SampleItem(
            sample_item_id=gen_id(),
            sample_batch_id=sample_item.sample_batch_id,
            filename=sample_item.filename,
            sample_item_name=sample_item.sample_item_name,
            sample_item_type=sample_item.sample_item_type,
            sample_item_attributes=sample_item.sample_item_attributes,
            sample_item_utc_created=datetime.utcnow(),
            sample_item_utc_modified=datetime.utcnow(),
            filter_id=sample_item.filter_id,
        )
        session.add(new_sample_item)
        await session.commit()
        await session.refresh(new_sample_item)

        if not new_sample_item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create sample item",
            )

        if not skipReload:
            await sio.emit(
                "sample_item_created",
                new_sample_item.sample_item_id,
                room=new_sample_item.sample_batch_id,
                namespace="/",
            )
        return new_sample_item


async def delete_sample_item(sample_item_id: str):
    async with async_session() as session:
        result = await session.execute(
            select(SampleItem).filter(SampleItem.sample_item_id == sample_item_id)
        )
        sample_item = result.scalar_one_or_none()
        if not sample_item:
            raise HTTPException(status_code=404, detail="Sample item not found")

        await session.delete(sample_item)
        await session.commit()
        await sio.emit(
            "sample_batch_reload",
            room=sample_item.sample_batch_id,
            namespace="/",
        )


async def update_sample_item(sample_item_id: str, sample_item: SampleItemUpdate):
    async with async_session() as session:
        db_sample_item = await session.get(SampleItem, sample_item_id)
        if not db_sample_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sample item not found",
            )

        for key, value in sample_item.dict(exclude_unset=True).items():
            setattr(db_sample_item, key, value)

        db_sample_item.sample_item_utc_modified = datetime.utcnow()

        await session.commit()
        await session.refresh(db_sample_item)

        await sio.emit(
            "sample_batch_reload",
            room=db_sample_item.sample_batch_id,
            namespace="/",
        )
        return db_sample_item


async def copy_sample_item(
    sample_item_id: str,
    sample_batch_id: str,
    sample_item_name: str,
    independent_transaction: bool = False,
    background_tasks: BackgroundTasks = None,
    sid=None,
) -> SampleItem:
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
    6. Emit success notification to user if called independently.
    7. Create task to compute the sample match data when called independently.

    :param sample_item_id: ID of the original sample item to be copied.
    :type sample_item_id: str
    :param sample_batch_id: ID of the sample batch where the new item will be placed.
    :type sample_batch_id: str
    :param sample_item_name: Name for the new copied sample item.
    :type sample_item_name: str
    :param independent_transaction: Indicates if this operation is part of a larger transaction or standalone, defaults to False
    :type independent_transaction: bool, optional
    :param background_tasks: FastAPI background tasks for computing matches post-copy, defaults to None
    :type background_tasks: BackgroundTasks, optional
    :param sid: Session ID, used for emitting notifications to specific clients, defaults to None
    :type sid: str, optional
    :raises HTTPException: If the original sample item is not found.
    :raises ValueError: For other validation or processing errors.
    :return: The newly created sample item instance.
    :rtype: SampleItem
    """
    try:
        async with async_session() as session:

            # Step 1: Validate the batch into which the sample is being copied.
            batch = await session.get(SampleBatch, sample_batch_id)

            if not batch:
                raise NotFoundException(
                    f"Sample batch with ID {sample_batch_id} not found"
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
                error_message = "Sample item not found"
                tech_message = (
                    f"{error_message}: wrong sample_item_id: {sample_item_id}"
                )
                if independent_transaction:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=error_message,
                    )
                else:
                    raise ValueError(tech_message)

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
                    "sample_item_utc_created": datetime.utcnow(),
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

        # Step 6: Emit success notification to user if called independently
        if independent_transaction and sid:
            success_payload = {
                "action": "copy",
                "type": "sample",
                "status": "success",
                "message": f"Sample '{sample_item_name}' was successfully copied to '{batch.sample_batch_name}'.",
                "progress_percentage": 100,
            }

            await sio.emit(
                "copy_finished",
                success_payload,
                room=sid,
                namespace="/",
            )

        # Step 7: Create task to compute the sample match data when called independently.
        if independent_transaction and background_tasks:
            background_tasks.add_task(
                match_sample_compute,
                sample_item_id=new_sample_item_id,
                added_target_compound_ids=None,
                added_ionization_mechanism_ids=None,
                independent_transaction=independent_transaction,
            )

        return new_sample_item
    # TODO_error_handling raise the ApiException that will be handled in copy sample endpoint or in copy batch operation
    except Exception as e:
        context_message = f"Failed to copy the sample item '{sample_item_name}'"
        api_exc = process_exception(e, context_message)
        raise ApiException(
            api_exc.user_message, api_exc.tech_message, api_exc.status_code
        )
