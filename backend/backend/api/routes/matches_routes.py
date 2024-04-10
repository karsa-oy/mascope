from fastapi import APIRouter, Depends
from ..utils.api_features import api_route
from ..controllers.matches_controller import get_match, get_matches
from ..models.pydantic_models.matches_pydantic_model import GetMatchesQueryParams

matches_router = APIRouter()


@matches_router.get("/api/matches")
@api_route()
async def get_matches_route(
    query_params: GetMatchesQueryParams = Depends(),
):
    return await get_matches(**query_params.dict())


@matches_router.get("/api/matches/{match_id}")
@api_route()
async def get_match_route(match_id: str):
    return await get_match(match_id)
