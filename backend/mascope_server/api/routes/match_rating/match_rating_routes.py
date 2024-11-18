from fastapi import APIRouter, Depends
from mascope_server.api.lib.api_features import api_route
from mascope_server.api.new.auth.dependencies import guest_user, editor_user
from mascope_server.api.controllers.match_rating.match_rating_controller import (
    get_match_ratings,
    get_match_rating,
    create_match_rating,
)
from mascope_server.api.models.match_rating.match_rating_pydantic_model import (
    MatchRatingCreate,
    GetMatchRatingsQueryParams,
)

match_rating_router = APIRouter(
    prefix="/api/match_ratings",
    tags=["Match Ratings"],
)


@match_rating_router.get("")
@api_route()
async def get_match_ratings_route(
    query_params: GetMatchRatingsQueryParams = Depends(),
    user=Depends(guest_user),
):
    """Retrieve a list of match ratings.

    :param query_params: Query parameters for filtering, sorting, and pagination.
    :type query_params: GetMatchRatingsQueryParams
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: A dictionary containing total count and list of match ratings.
    :rtype: dict
    """
    return await get_match_ratings(**query_params.model_dump())


@match_rating_router.get("/{match_rating_id}")
@api_route()
async def get_match_rating_route(
    match_rating_id: str,
    user=Depends(guest_user),
):
    """Retrieve details of a specific match rating by ID.

    :param match_rating_id: Unique identifier of the match rating.
    :type match_rating_id: str
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: The requested match rating's details.
    :rtype: dict
    """
    return await get_match_rating(match_rating_id=match_rating_id)


@match_rating_router.post("")
@api_route(
    status_code=201,
)
async def create_match_rating_route(
    match_rating: MatchRatingCreate,
    user=Depends(editor_user),
):
    """Submit a new match rating.

    :param match_rating: The match rating to create.
    :type match_rating: MatchRatingCreate
    :param user: The current authenticated user with editor permissions.
    :type user: User
    :return: A dictionary with the created match rating details.
    :rtype: dict
    """
    return await create_match_rating(match_rating=match_rating)
