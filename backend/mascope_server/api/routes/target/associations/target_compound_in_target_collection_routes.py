from fastapi import APIRouter, Depends
from mascope_server.api.lib.api_features import api_route
from mascope_server.api.controllers.target.associations.target_compound_in_target_collection_controller import (
    get_target_compound_in_target_collection,
)
from mascope_server.api.models.target.compounds.target_compound_pydantic_model import (
    GetTargetCompoundInTargetCollectionQueryParams,
)

target_compound_in_target_collection_router = APIRouter()


@target_compound_in_target_collection_router.get(
    "/api/target/associations/target_compound_in_target_collections"
)
@api_route()
async def get_target_compound_in_target_collections_route(
    query_params: GetTargetCompoundInTargetCollectionQueryParams = Depends(),
):
    return await get_target_compound_in_target_collection(**query_params.model_dump())
