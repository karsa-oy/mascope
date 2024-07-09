from typing import List
from fastapi import APIRouter, Depends
from mascope_server.api.utils.api_features import api_route
from mascope_server.api.controllers.match.match_compounds_controller import (
    get_match_compounds,
    get_match_compound,
    create_match_compounds,
    delete_match_compounds,
)
from mascope_server.api.models.pydantic_models.match_compound_pydantic_model import (
    MatchCompoundBase,
    GetMatchCompoundsQueryParams,
    DeleteMatchCompounsPayload,
)

match_compounds_router = APIRouter()


@match_compounds_router.get("/api/match/compounds")
@api_route()
async def get_all_match_compounds_route(
    query_params: GetMatchCompoundsQueryParams = Depends(),
):
    return await get_match_compounds(**query_params.dict())


@match_compounds_router.get("/api/match/compounds/{match_compound_id}")
@api_route()
async def get_match_compound_route(match_compound_id: str):
    return await get_match_compound(match_compound_id)


@match_compounds_router.post("/api/match/compounds")
@api_route(status_code=201)
async def create_match_compounds_route(body: List[MatchCompoundBase]):
    return await create_match_compounds(
        match_compounds=body, independent_transaction=True
    )


@match_compounds_router.delete("/api/match/compounds")
@api_route()
async def delete_match_compounds_route(body: DeleteMatchCompounsPayload):
    return await delete_match_compounds(
        sample_item_id=body.sample_item_id,
        sample_batch_id=body.sample_batch_id,
        target_compound_ids=body.target_compound_ids,
    )
