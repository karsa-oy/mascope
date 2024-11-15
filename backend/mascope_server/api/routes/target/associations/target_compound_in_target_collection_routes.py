from fastapi import APIRouter, Depends
from mascope_server.api.new.auth.dependencies import guest_user
from mascope_server.api.lib.api_features import api_route
from mascope_server.api.controllers.target.associations.target_compound_in_target_collection_controller import (
    get_target_compound_in_target_collection,
)
from mascope_server.api.models.target.compounds.target_compound_pydantic_model import (
    GetTargetCompoundInTargetCollectionQueryParams,
)

target_compound_in_target_collection_router = APIRouter(
    prefix="/api/target/associations/target_compound_in_target_collections",
    tags=["Target Compound Associations"],
)


@target_compound_in_target_collection_router.get("")
@api_route()
async def get_target_compound_in_target_collections_route(
    query_params: GetTargetCompoundInTargetCollectionQueryParams = Depends(),
    user=Depends(guest_user),
):
    """Retrieve target compound ids associated with a target collection.

    :param query_params: Query parameters for filtering, sorting, and pagination.
    :param user: The current authenticated user with guest permissions.
    :return: A dictionary containing the total count and list of target compounds in target collection.
    """
    return await get_target_compound_in_target_collection(**query_params.model_dump())
