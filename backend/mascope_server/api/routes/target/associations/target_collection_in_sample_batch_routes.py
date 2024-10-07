from fastapi import APIRouter, Depends
from mascope_server.api.lib.api_features import api_route
from mascope_server.api.controllers.target.associations.target_collection_in_sample_batch_controller import (
    get_target_collections_in_sample_batch,
)
from mascope_server.api.models.target.collections.target_collection_pydantic_model import (
    GetTargetCollectionsInSampleBatchQueryParams,
)


target_collection_in_sample_batch_router = APIRouter()


@target_collection_in_sample_batch_router.get(
    "/api/target/associations/target_collections_in_sample_batch"
)
@api_route()
async def get_target_collections_in_sample_batch_route(
    query_params: GetTargetCollectionsInSampleBatchQueryParams = Depends(),
):
    return await get_target_collections_in_sample_batch(**query_params.model_dump())
