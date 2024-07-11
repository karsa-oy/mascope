from fastapi import APIRouter, Depends
from ..utils.api_features import api_route
from ..controllers.target_collection_in_sample_batch_controller import (
    get_target_collections_in_sample_batch,
)
from ..models.pydantic_models.target_collection_pydantic_model import (
    GetTargetCollectionsInSampleBatchQueryParams,
)


target_collection_in_sample_batch_router = APIRouter()


@target_collection_in_sample_batch_router.get("/api/target_collections_in_sample_batch")
@api_route()
async def get_target_collections_in_sample_batch_route(
    query_params: GetTargetCollectionsInSampleBatchQueryParams = Depends(),
):
    return await get_target_collections_in_sample_batch(**query_params.model_dump())
