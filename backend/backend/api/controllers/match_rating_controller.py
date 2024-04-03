import json
from fastapi import HTTPException, status
from sqlalchemy import asc, desc, func, and_
from sqlalchemy.future import select
from datetime import datetime
from backend.api_sio import sio
from backend.db import async_session
from backend.db.id import gen_id
from ..models.models import MatchRating
from ..models.pydantic_models.match_rating_pydantic_model import (
    MatchRatingCreate,
)


async def create_match_rating(match_rating: MatchRatingCreate):
    async with async_session() as session:
        new_match_rating = MatchRating(
            match_rating_id=gen_id(32),
            sample_item_id=match_rating.sample_item_id,
            target_ion_id=match_rating.target_ion_id,
            rating=match_rating.rating,
            # Convert Pydantic model to dictionary and then to JSON string
            checklist=json.dumps(
                match_rating.checklist.dict() if match_rating.checklist else {}
            ),
            environment=json.dumps(match_rating.environment.dict()),
            match_rating_utc_created=datetime.utcnow(),
        )
        session.add(new_match_rating)
        await session.commit()
        await session.refresh(new_match_rating)

        if not new_match_rating:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create match rating",
            )

        # Deserialize from JSON string
        new_match_rating.checklist = json.loads(new_match_rating.checklist)
        new_match_rating.environment = json.loads(new_match_rating.environment)

        return new_match_rating


async def get_match_ratings(
    sample_item_id: str = None,
    target_ion_id: str = None,
    rating: int = None,
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 100,
    minDatetime: datetime = None,
    maxDatetime: datetime = None,
):
    async with async_session() as session:
        stmt = select(MatchRating)

        if sample_item_id:
            stmt = stmt.filter(MatchRating.sample_item_id == sample_item_id)

        if target_ion_id:
            stmt = stmt.filter(MatchRating.target_ion_id == target_ion_id)

        if rating:
            stmt = stmt.filter(MatchRating.rating == rating)

        if minDatetime and maxDatetime:
            stmt = stmt.where(
                and_(
                    MatchRating.match_rating_utc_created >= minDatetime,
                    MatchRating.match_rating_utc_created <= maxDatetime,
                )
            )

        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(MatchRating, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(MatchRating, sort)))

        # Get total count
        count_stmt = select(func.count()).select_from(stmt)
        total = await session.scalar(count_stmt)

        # Get paginated results
        stmt = stmt.offset(page * limit).limit(limit)
        result = await session.execute(stmt)
        match_ratings = result.scalars().all()

        # Deserialize from JSON string
        for match_rating in match_ratings:
            if isinstance(match_rating.checklist, str):
                match_rating.checklist = json.loads(match_rating.checklist)
            if isinstance(match_rating.environment, str):
                match_rating.environment = json.loads(match_rating.environment)

        return {
            "results": total,
            "data": [match_rating.to_dict() for match_rating in match_ratings],
        }


async def get_match_rating_by_id(match_rating_id: str):
    async with async_session() as session:
        stmt = select(MatchRating).filter(
            MatchRating.match_rating_id == match_rating_id
        )
        result = await session.execute(stmt)
        match_rating = result.scalars().first()

        if not match_rating:
            raise HTTPException(
                status_code=404,
                detail=f"MatchRating with ID {match_rating_id} not found",
            )

        # Deserialize from JSON string
        match_rating.checklist = json.loads(match_rating.checklist)
        match_rating.environment = json.loads(match_rating.environment)

        return match_rating.to_dict()
