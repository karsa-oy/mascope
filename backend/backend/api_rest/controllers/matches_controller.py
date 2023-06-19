from fastapi import HTTPException
from sqlalchemy import asc, desc, func
from sqlalchemy.future import select

from backend.db_api_rest import async_session
from ..models.models import Match


async def get_matches(
    sample_item_id: str,
    target_isotope_id: str,
    sort: str,
    order: str,
    page: int,
    limit: int,
):
    async with async_session() as session:
        stmt = select(Match)

        if sample_item_id:
            stmt = stmt.filter(Match.sample_item_id == sample_item_id)

        if target_isotope_id:
            stmt = stmt.filter(Match.target_isotope_id == target_isotope_id)

        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(Match, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(Match, sort)))

        # Get total count
        count_stmt = select(func.count()).select_from(stmt)
        total = await session.scalar(count_stmt)

        # Get paginated results
        stmt = stmt.offset(page * limit).limit(limit)
        result = await session.execute(stmt)
        matches = result.scalars().all()

        return {
            "results": total,
            "data": [match.to_dict() for match in matches],
        }


async def get_match_by_id(match_id: str):
    async with async_session() as session:
        stmt = select(Match).filter(Match.match_id == match_id)
        result = await session.execute(stmt)
        match = result.scalars().first()

        if not match:
            raise HTTPException(
                status_code=404,
                detail=f"Match with ID {match_id} not found",
            )

        return match.to_dict()
