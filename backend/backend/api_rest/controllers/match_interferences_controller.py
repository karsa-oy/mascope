from fastapi import HTTPException
from sqlalchemy import asc, desc, func
from sqlalchemy.future import select
from backend.db_api_rest import async_session
from ..models.models import MatchInterference


async def get_match_interferences(
    target_isotope_id: str,
    sample_item_id: str,
    min_sample_peak_interference: float,
    max_sample_peak_interference: float,
    sort: str,
    order: str,
    page: int,
    limit: int,
):
    async with async_session() as session:
        stmt = select(MatchInterference)

        if target_isotope_id:
            stmt = stmt.filter(MatchInterference.target_isotope_id == target_isotope_id)

        if sample_item_id:
            stmt = stmt.filter(MatchInterference.sample_item_id == sample_item_id)

        if min_sample_peak_interference is not None:
            stmt = stmt.filter(
                MatchInterference.sample_peak_interference
                >= min_sample_peak_interference
            )

        if max_sample_peak_interference is not None:
            stmt = stmt.filter(
                MatchInterference.sample_peak_interference
                <= max_sample_peak_interference
            )

        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(MatchInterference, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(MatchInterference, sort)))

        # Get total count
        count_stmt = select(func.count()).select_from(stmt)
        total = await session.scalar(count_stmt)

        # Get paginated results
        stmt = stmt.offset(page * limit).limit(limit)
        result = await session.execute(stmt)
        match_interferences = result.scalars().all()

        return {
            "results": total,
            "data": [
                match_interference.to_dict()
                for match_interference in match_interferences
            ],
        }


async def get_match_interference_by_id(match_interference_id: str):
    async with async_session() as session:
        stmt = select(MatchInterference).filter(
            MatchInterference.match_interference_id == match_interference_id
        )
        result = await session.execute(stmt)
        match_interference = result.scalars().first()

        if not match_interference:
            raise HTTPException(
                status_code=404,
                detail=f"MatchInterference with ID {match_interference_id} not found",
            )

        return match_interference.to_dict()
