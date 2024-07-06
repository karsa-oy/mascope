from typing import List
from fastapi import APIRouter, Depends
from mascope_server.api.utils.api_features import api_route
from mascope_server.api.controllers.match.match_isotopes_controller import (
    get_match_isotope,
    get_match_isotopes,
    create_match_isotopes,
    delete_match_isotopes,
)
from mascope_server.api.models.pydantic_models.match_isotopes_pydantic_model import (
    MatchIsotopeBase,
    GetMatchesQueryParams,
    DeleteMatchIsotopesPayload,
)


match_isotopes_router = APIRouter()


@match_isotopes_router.get("/api/match/isotopes")
@api_route()
async def get_match_isotopes_route(
    query_params: GetMatchesQueryParams = Depends(),
):
    return await get_match_isotopes(**query_params.dict())


@match_isotopes_router.get("/api/match/isotopes/{match_isotope_id}")
@api_route()
async def get_match_isotope_route(match_isotope_id: str):
    return await get_match_isotope(match_isotope_id)


@match_isotopes_router.post("/api/match/isotopes")
@api_route(status_code=201)
async def create_match_isotopes_route(body: List[MatchIsotopeBase]):
    return await create_match_isotopes(
        match_isotopes=body, independent_transaction=True
    )


@match_isotopes_router.delete("/api/match/isotopes")
@api_route()
async def delete_match_isotopes_route(body: DeleteMatchIsotopesPayload):
    return await delete_match_isotopes(
        sample_item_id=body.sample_item_id,
        sample_batch_id=body.sample_batch_id,
        target_isotope_ids=body.target_isotope_ids,
    )
