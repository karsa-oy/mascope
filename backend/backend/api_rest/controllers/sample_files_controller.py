from fastapi import HTTPException
from sqlalchemy import asc, desc, func, and_, cast, Float
from sqlalchemy.future import select
from datetime import datetime
from backend.db_api_rest import async_session

from ..models.models import SampleFile


async def get_sample_files(
    sort: str,
    order: str,
    page: int,
    limit: int,
    minDatetime: datetime = None,
    maxDatetime: datetime = None,
    instrument: str = None,
):
    async with async_session() as session:
        stmt = select(SampleFile)

        if minDatetime and maxDatetime:
            stmt = stmt.where(
                and_(
                    cast(func.julianday(SampleFile.datetime_utc), Float)
                    >= func.julianday(minDatetime),
                    cast(func.julianday(SampleFile.datetime_utc), Float)
                    <= func.julianday(maxDatetime),
                )
            )

        if instrument:
            stmt = stmt.where(SampleFile.instrument == instrument)

        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(SampleFile, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(SampleFile, sort)))

        # Get total count
        count_stmt = select(func.count()).select_from(stmt)
        total = await session.scalar(count_stmt)

        # Get paginated results
        stmt = stmt.offset(page * limit).limit(limit)
        result = await session.execute(stmt)
        sample_files = result.scalars().all()

        return {
            "results": total,
            "data": [sample_file.to_dict() for sample_file in sample_files],
        }


async def get_mz_calibration(
    instrument: str,
):
    async with async_session() as session:
        stmt = select(SampleFile.mz_calibration).where(
            and_(
                SampleFile.instrument == instrument,
                SampleFile.mz_calibration.isnot(None),
                SampleFile.datetime_utc
                == select(func.max(SampleFile.datetime_utc))
                .where(
                    and_(
                        SampleFile.instrument == instrument,
                        SampleFile.mz_calibration.isnot(None),
                    )
                )
                .scalar_subquery(),
            )
        )

        result = await session.execute(stmt)
        mz_calibration = result.scalars().first()

        return mz_calibration


async def get_sample_file_by_id(sample_file_id: str):
    async with async_session() as session:
        stmt = select(SampleFile).filter(SampleFile.sample_file_id == sample_file_id)
        result = await session.execute(stmt)
        sample_file = result.scalars().first()

        if not sample_file:
            raise HTTPException(
                status_code=404,
                detail=f"SampleFile with ID {sample_file_id} not found",
            )

        return sample_file.to_dict()
