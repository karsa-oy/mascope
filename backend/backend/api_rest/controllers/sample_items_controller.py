import re
from fastapi import HTTPException, status
from sqlalchemy import asc, desc, func, and_
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from datetime import datetime

from backend.server import sio
from backend.db_api_rest import async_session
from backend.db.id import gen_id

from ..models.models import (
    SampleFile,
    SampleItem,
    Match,
    MatchInterference,
    MatchRating,
)
from ..models.pydantic_models.sample_item_pydantic_model import (
    SampleItemCreate,
    SampleItemUpdate,
)


async def get_sample_item_by_id(sample_item_id: str):
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


async def get_sample_items(
    sample_batch_id: str = None,
    filename: str = None,
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 10000,
    include_tic: bool = False,
    include_intensity: bool = False,
    compounds: str = "",
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

        if include_tic or include_intensity:
            stmt = stmt.options(joinedload(SampleItem.sample_file))

        # Get total count
        count_stmt = select(func.count()).select_from(stmt)
        total = await session.scalar(count_stmt)

        # Get paginated results
        stmt = stmt.offset(page * limit).limit(limit)
        result = await session.execute(stmt)
        sample_items = result.scalars().all()

        # If 'include_tic' or 'include_intensity' is True, manually added 'tic' field to the response
        if include_tic or include_intensity:
            for sample_item in sample_items:
                sample_item.tic = (
                    sample_item.sample_file.tic if sample_item.sample_file else None
                )

        # If 'include_intensity' is True, get the compound intensity and add it to the response
        if include_intensity and compounds:
            # Split the compounds string into a list
            compound_list = compounds.split(",")
            for sample_item in sample_items:
                # Pass the list instead of the string
                await sample_item.get_compound_intensity(session, compound_list)

        return {
            "results": total,
            "data": [
                sample_item.to_dict(
                    include_tic=include_tic,
                    include_intensity=include_intensity,
                    compounds=compounds,
                )
                for sample_item in sample_items
            ],
        }


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


async def copy_sample_item(sample_item_id: str, sample_batch_id: str, session=None):
    independent_transaction = False

    if session is None:
        independent_transaction = True
        session = async_session()

    async with session.begin_nested() if not independent_transaction else session:
        # Fetch the original sample_item along with related Match, MatchInterference, and MatchRating records
        stmt = (
            select(SampleItem)
            .options(
                joinedload(SampleItem.match),
                joinedload(SampleItem.match_interference),
                joinedload(SampleItem.match_rating),
            )
            .filter(SampleItem.sample_item_id == sample_item_id)
        )
        result = await session.execute(stmt)
        original_sample_item = result.scalars().first()

        if not original_sample_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Sample item not found"
            )

        # # # # Sample item naming logic # # # #
        # Initial new sample item name
        new_sample_item_name = original_sample_item.sample_item_name
        name_exists = True  # Control variable for the loop
        copy_num = 0  # Starting copy number

        while name_exists:
            # Query to check if a sample item with the new name already exists in the specified sample batch
            stmt = select(SampleItem).filter(
                and_(
                    SampleItem.sample_item_name == new_sample_item_name,
                    SampleItem.sample_batch_id == sample_batch_id,
                )
            )
            result = await session.execute(stmt)
            existing_sample_item = result.scalar_one_or_none()

            if existing_sample_item is None:
                # Exit the loop if the name is unique, keep the original name
                name_exists = False
            else:
                # Name pattern matching and modification
                name_pattern = re.search(
                    r"(.*\sCopy)(?:\((\d+)\))?$", new_sample_item_name
                )

                if name_pattern:
                    base_name = name_pattern.group(1)
                    copy_num = name_pattern.group(2)

                    if copy_num:
                        # Increment the number by 1 if it exists
                        new_sample_item_name = f"{base_name}({int(copy_num) + 1})"
                    else:
                        # Append "(1)" if the name ends with " Copy"
                        new_sample_item_name = f"{base_name}(1)"
                else:
                    # Append " Copy" if the name doesn't fit the pattern
                    new_sample_item_name = f"{new_sample_item_name} Copy"

        # Create a new sample_item with a new ID, name, batch and time of creation, but copy all other data
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
                "sample_item_name": new_sample_item_name,
                "sample_item_utc_created": datetime.utcnow(),
            }
        )
        new_sample_item = SampleItem(**new_sample_item_data)
        session.add(new_sample_item)

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
            new_match_interference = MatchInterference(**new_match_interference_data)
            session.add(new_match_interference)

        # Copy related MatchRating records
        for match_rating in original_sample_item.match_rating:
            new_match_rating_data = {
                c.name: getattr(match_rating, c.name)
                for c in MatchRating.__table__.columns
                if c.name != "match_rating_id"
            }
            new_match_rating_data.update(
                {
                    "match_rating_id": gen_id(32),
                    "sample_item_id": new_sample_item_id,
                }
            )
            new_match_rating = MatchRating(**new_match_rating_data)
            session.add(new_match_rating)

        if independent_transaction:
            # Commit the transaction to save the data
            await session.commit()
            # Reload affected sample batch
            await sio.emit("sample_batch_reload", room=sample_batch_id, namespace="/")
        else:
            # If it is a nested transaction, commit it before returning, this creates a savepoint.
            await session.commit()

        return new_sample_item
