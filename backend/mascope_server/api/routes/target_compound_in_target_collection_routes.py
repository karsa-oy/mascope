from fastapi import APIRouter, Depends
from ..utils.api_features import api_route
from ..controllers.target_compound_in_target_collection_controller import (
    get_target_compound_in_target_collection,
)
from ..models.pydantic_models.target_compound_pydantic_model import (
    GetTargetCompoundInTargetCollectionQueryParams,
)

target_compound_in_target_collection_router = APIRouter()


@target_compound_in_target_collection_router.get(
    "/api/target_compound_in_target_collections"
)
@api_route()
async def get_target_compound_in_target_collections_route(
    query_params: GetTargetCompoundInTargetCollectionQueryParams = Depends(),
):
    return await get_target_compound_in_target_collection(**query_params.model_dump())
