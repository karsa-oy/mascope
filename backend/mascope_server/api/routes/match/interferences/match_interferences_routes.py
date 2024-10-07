from typing import List
from fastapi import APIRouter, Depends
from mascope_server.api.lib.api_features import api_route
from mascope_server.api.controllers.match.interferences.match_interferences_controller import (
    get_match_interference,
    get_match_interferences,
    create_match_interferences,
    delete_match_interferences,
)
from mascope_server.api.models.match.interferences.match_interferences_pydantic_model import (
    MatchInterferenceBase,
    GetMatchInterferencesQueryParams,
    DeleteMatchInterferencesPayload,
)

match_interferences_router = APIRouter()


@match_interferences_router.get("/api/match/interferences")
@api_route()
async def get_match_interferences_route(
    query_params: GetMatchInterferencesQueryParams = Depends(),
):
    return await get_match_interferences(**query_params.model_dump())


@match_interferences_router.get("/api/match/interferences/{match_interference_id}")
@api_route()
async def get_match_interference_route(match_interference_id: str):
    return await get_match_interference(match_interference_id)


@match_interferences_router.post("/api/match/interferences")
@api_route(status_code=201)
async def create_match_interferences_route(body: List[MatchInterferenceBase]):
    return await create_match_interferences(
        match_interferences=body, independent_transaction=True
    )


@match_interferences_router.delete("/api/match/interferences")
@api_route()
async def delete_match_interferences_route(body: DeleteMatchInterferencesPayload):
    return await delete_match_interferences(
        sample_item_id=body.sample_item_id,
        sample_batch_id=body.sample_batch_id,
        target_isotope_ids=body.target_isotope_ids,
    )
