from fastapi import HTTPException
from sqlalchemy import asc, desc, func
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from backend.db_api_rest import async_session

from ..models.models import SampleFile, SampleItem


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


# _____________________________________________________________________________________________________________
