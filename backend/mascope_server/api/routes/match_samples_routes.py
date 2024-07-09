from typing import List
from fastapi import APIRouter, Depends
from mascope_server.api.utils.api_features import api_route
from mascope_server.api.controllers.match.match_samples_controller import (
    get_match_samples,
    get_match_sample,
    create_match_samples,
    delete_match_samples,
)
from mascope_server.api.models.pydantic_models.match_sample_pydantic_model import (
    MatchSampleBase,
    GetMatchSamplesQueryParams,
)
from mascope_server.api.models.pydantic_models.match_pydantic_model import (
    FilterSamplePayload,
)

match_samples_router = APIRouter()


@match_samples_router.get("/api/match/samples")
@api_route()
async def get_match_samples_route(
    query_params: GetMatchSamplesQueryParams = Depends(),
):
    return await get_match_samples(**query_params.dict())


@match_samples_router.get("/api/match/samples/{match_sample_id}")
@api_route()
async def get_match_sample_route(match_sample_id: str):
    return await get_match_sample(match_sample_id)


@match_samples_router.post("/api/match/samples")
@api_route(status_code=201)
async def create_match_samples_route(body: List[MatchSampleBase]):
    return await create_match_samples(match_samples=body, independent_transaction=True)


@match_samples_router.delete("/api/match/samples")
@api_route()
async def delete_match_samples_route(body: FilterSamplePayload):
    return await delete_match_samples(
        sample_item_id=body.sample_item_id,
        sample_batch_id=body.sample_batch_id,
    )
