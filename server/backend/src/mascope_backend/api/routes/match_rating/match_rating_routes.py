from fastapi import APIRouter, Depends

from mascope_backend.api.controllers.match_rating.match_rating_controller import (
    create_match_rating,
    get_match_rating,
    get_match_ratings,
)
from mascope_backend.api.lib.api_features import api_route
from mascope_backend.api.models.match_rating.match_rating_pydantic_model import (
    GetMatchRatingsQueryParams,
    MatchRatingCreate,
)
from mascope_backend.api.new.auth.dependencies import current_active_user
from mascope_backend.api.new.workspaces.dependencies import check_sample_access
from mascope_backend.db import User


match_rating_router = APIRouter(
    prefix="/api/match_ratings",
    tags=["Match Ratings"],
)


@match_rating_router.get("")
@api_route()
async def get_match_ratings_route(
    query_params: GetMatchRatingsQueryParams = Depends(),
    user: User = Depends(current_active_user),
):
    """Retrieve a list of match ratings.

    :param query_params: Query parameters for filtering, sorting, and pagination.
    :type query_params: GetMatchRatingsQueryParams
    :param user: The current authenticated user. Requires workspace guest role.
    :type user: User
    :return: A dictionary containing total count and list of match ratings.
    :rtype: dict
    """
    if query_params.sample_item_id:
        await check_sample_access(query_params.sample_item_id, user, "guest")
    return await get_match_ratings(**query_params.model_dump())


@match_rating_router.get("/{match_rating_id}")
@api_route()
async def get_match_rating_route(
    match_rating_id: str,
    user: User = Depends(current_active_user),
):
    """Retrieve details of a specific match rating by ID.

    :param match_rating_id: Unique identifier of the match rating.
    :type match_rating_id: str
    :param user: The current authenticated user. Requires workspace guest role.
    :type user: User
    :return: The requested match rating's details.
    :rtype: dict
    """
    result = await get_match_rating(match_rating_id=match_rating_id)
    await check_sample_access(result["data"]["sample_item_id"], user, "guest")
    return result


@match_rating_router.post("")
@api_route(
    status_code=201,
)
async def create_match_rating_route(
    match_rating: MatchRatingCreate,
    user: User = Depends(current_active_user),
):
    """Submit a new match rating.

    :param match_rating: The match rating to create.
    :type match_rating: MatchRatingCreate
    :param user: The current authenticated user. Requires workspace editor role.
    :type user: User
    :return: A dictionary with the created match rating details.
    :rtype: dict
    """
    await check_sample_access(match_rating.sample_item_id, user, "editor")
    return await create_match_rating(match_rating=match_rating)
