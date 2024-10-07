from fastapi import APIRouter, Depends
from mascope_server.api.lib.api_features import api_route
from mascope_server.api.controllers.match_rating.match_rating_controller import (
    get_match_ratings,
    get_match_rating,
    create_match_rating,
)
from mascope_server.api.models.match_rating.match_rating_pydantic_model import (
    MatchRatingCreate,
    GetMatchRatingsQueryParams,
)

match_rating_router = APIRouter()


@match_rating_router.get("/api/match_ratings")
@api_route()
async def get_match_ratings_route(
    query_params: GetMatchRatingsQueryParams = Depends(),
):
    return await get_match_ratings(**query_params.model_dump())


@match_rating_router.get("/api/match_ratings/{match_rating_id}")
@api_route()
async def get_match_rating_route(match_rating_id: str):
    return await get_match_rating(match_rating_id=match_rating_id)


@match_rating_router.post("/api/match_ratings")
@api_route(
    status_code=201,
    include_message=True,
    success_message="Rating submitted successfully. Thanks for your feedback!",
    error_message="Failed to submit rating. Please try again.",
)
async def create_match_rating_route(match_rating: MatchRatingCreate):
    return await create_match_rating(match_rating=match_rating)
