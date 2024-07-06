from typing import List
from fastapi import APIRouter, Depends
from mascope_server.api.utils.api_features import api_route
from mascope_server.api.controllers.match.match_ions_controller import (
    create_match_ions,
    delete_match_ions,
)
from mascope_server.api.models.pydantic_models.match_ion_pydantic_model import (
    MatchIonBase,
    DeleteMatchIonsPayload,
)


match_ions_router = APIRouter()


# @match_ions_router.get("/api/match/ions")
# @api_route()
# async def get_match_ions_route(
#     query_params: GetMatchesQueryParams = Depends(),
# ):
#     return await get_match_ions(**query_params.dict())


# @match_ions_router.get("/api/match/ions/{match_ion_id}")
# @api_route()
# async def get_match_ion_route(match_ion_id: str):
#     return await get_match_ion(match_ion_id)


@match_ions_router.post("/api/match/ions")
@api_route(status_code=201)
async def create_match_ions_route(body: List[MatchIonBase]):
    return await create_match_ions(match_ions=body, independent_transaction=True)


@match_ions_router.delete("/api/match/ions")
@api_route()
async def delete_match_ions_route(body: DeleteMatchIonsPayload):
    return await delete_match_ions(
        sample_item_id=body.sample_item_id,
        sample_batch_id=body.sample_batch_id,
        target_ion_ids=body.target_ion_ids,
    )
