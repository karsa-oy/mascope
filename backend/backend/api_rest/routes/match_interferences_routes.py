from fastapi import APIRouter, Depends
from ..utils.api_features import api_route
from ..controllers.match_interferences_controller import (
    get_match_interference,
    get_match_interferences,
)
from ..models.pydantic_models.match_interferences_pydantic_model import (
    GetMatchInterferencesQueryParams,
)

match_interferences_router = APIRouter()


@match_interferences_router.get("/api/match_interferences")
@api_route()
async def get_match_interferences_route(
    query_params: GetMatchInterferencesQueryParams = Depends(),
):
    return await get_match_interferences(**query_params.dict())


@match_interferences_router.get("/api/match_interferences/{match_interference_id}")
@api_route()
async def get_match_interference_route(match_interference_id: str):
    return await get_match_interference(match_interference_id)
