from fastapi import APIRouter, Depends
from mascope_server.api.lib.api_features import api_route
from mascope_server.api.controllers.samples.samples_controller import (
    get_samples,
    get_sample,
)
from mascope_server.api.models.samples.sample_pydantic_model import (
    GetSamplesQueryParams,
)

samples_router = APIRouter()


@samples_router.get("/api/samples", tags=["Samples Loading"])
@api_route()
async def get_samples_route(
    query_params: GetSamplesQueryParams = Depends(),
):
    return await get_samples(**query_params.model_dump())


@samples_router.get("/api/samples/{sample_item_id}")
@api_route()
async def get_sample_route(
    sample_item_id: str,
):
    return await get_sample(sample_item_id=sample_item_id)
