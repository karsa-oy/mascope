from fastapi import APIRouter, Depends

from mascope_backend.api.controllers.target.associations.target_collection_in_sample_batch_controller import (
    get_target_collections_in_sample_batch,
)
from mascope_backend.api.lib.api_features import api_route
from mascope_backend.api.models.target.collections.target_collection_pydantic_model import (
    GetTargetCollectionsInSampleBatchQueryParams,
)
from mascope_backend.api.new.auth.dependencies import guest_user


target_collection_in_sample_batch_router = APIRouter(
    prefix="/api/target/associations/target_collections_in_sample_batch",
    tags=["Target Collection Associations"],
)


@target_collection_in_sample_batch_router.get("")
@api_route()
async def get_target_collections_in_sample_batch_route(
    query_params: GetTargetCollectionsInSampleBatchQueryParams = Depends(),
    user=Depends(guest_user),
):
    """Retrieve target collection ids associated with a sample batch.

    :param query_params: Query parameters for filtering, sorting, and pagination.
    :param user: The current authenticated user with guest permissions.
    :return: A dictionary containing the total count and list of target collections in sample batch.
    """
    return await get_target_collections_in_sample_batch(**query_params.model_dump())
