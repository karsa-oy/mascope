from fastapi import APIRouter
from datetime import datetime
from ..controllers.match_rating_controller import (
    get_match_rating_by_id,
    get_match_ratings,
    create_match_rating,
)
from ..models.pydantic_models.match_rating_pydantic_model import MatchRatingCreate

match_rating_router = APIRouter()


@match_rating_router.post("/api/match_ratings")
async def create_match_rating_route(match_rating: MatchRatingCreate):
    return await create_match_rating(match_rating)


@match_rating_router.get("/api/match_ratings")
async def get_match_ratings_route(
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
    return await get_match_ratings(
        sample_item_id,
        target_ion_id,
        rating,
        sort,
        order,
        page,
        limit,
        minDatetime,
        maxDatetime,
    )


@match_rating_router.get("/api/match_ratings/{match_rating_id}")
async def get_match_rating_by_id_route(match_rating_id: str):
    return await get_match_rating_by_id(match_rating_id)
