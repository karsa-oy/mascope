from fastapi import HTTPException, status
from sqlalchemy import asc, desc, func
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from datetime import datetime
import json

from backend.server import sio
from backend.db_api_rest import async_session
from backend.db.id import gen_id

from ..models.models import SampleFile, SampleItem
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


async def create_sample_item(sample_item: SampleItemCreate):
    async with async_session() as session:
        new_sample_item = SampleItem(
            sample_item_id=gen_id(),
            sample_batch_id=sample_item.sample_batch_id,
            filename=sample_item.filename,
            sample_item_name=sample_item.sample_item_name,
            sample_item_type=sample_item.sample_item_type,
            sample_item_attributes=json.dumps(sample_item.sample_item_attributes),
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
            if key == "sample_item_attributes":
                value = json.dumps(value)  # Serialize the dictionary before storing
            setattr(db_sample_item, key, value)

        db_sample_item.sample_item_utc_modified = datetime.utcnow()

        await session.commit()
        await session.refresh(db_sample_item)

        db_sample_item.sample_item_attributes = json.loads(
            db_sample_item.sample_item_attributes
        )  # Deserialize the data back into dictionary format

        await sio.emit(
            "sample_batch_reload",
            room=db_sample_item.sample_batch_id,
            namespace="/",
        )
        return db_sample_item
