from fastapi import APIRouter, Depends
from mascope_server.api.utils.api_features import api_route
from mascope_server.api.controllers.match.sample.match_sample_targets_controller import (
    get_match_sample_collections,
    get_match_sample_compounds,
    get_match_sample_ions,
    get_match_sample_isotopes,
)
from mascope_server.api.models.pydantic_models.match.sample.match_sample_targets_pydantic_model import (
    SortingPaginationQueryParams,
    GetMatchSampleCompoundsQueryParams,
    GetMatchSampleIonsQueryParams,
    GetMatchSampleIsotopesQueryParams,
)

match_sample_targets_router = APIRouter()


@match_sample_targets_router.get(
    "/api/match/sample/{sample_item_id}/collections", tags=["Sample Match Loading"]
)
@api_route()
async def get_match_sample_collections_route(
    sample_item_id: str,
    query_params: SortingPaginationQueryParams = Depends(),
):
    return await get_match_sample_collections(
        sample_item_id=sample_item_id, **query_params.model_dump()
    )


@match_sample_targets_router.get(
    "/api/match/sample/{sample_item_id}/compounds", tags=["Sample Match Loading"]
)
@api_route()
async def get_match_sample_compounds_route(
    sample_item_id: str,
    query_params: GetMatchSampleCompoundsQueryParams = Depends(),
):
    return await get_match_sample_compounds(
        sample_item_id=sample_item_id, **query_params.model_dump()
    )


@match_sample_targets_router.get(
    "/api/match/sample/{sample_item_id}/ions", tags=["Sample Match Loading"]
)
@api_route()
async def get_match_sample_ions_route(
    sample_item_id: str,
    query_params: GetMatchSampleIonsQueryParams = Depends(),
):
    return await get_match_sample_ions(
        sample_item_id=sample_item_id, **query_params.model_dump()
    )


@match_sample_targets_router.get(
    "/api/match/sample/{sample_item_id}/isotopes", tags=["Sample Match Loading"]
)
@api_route()
async def get_match_sample_isotopes_route(
    sample_item_id: str,
    query_params: GetMatchSampleIsotopesQueryParams = Depends(),
):
    return await get_match_sample_isotopes(
        sample_item_id=sample_item_id, **query_params.model_dump()
    )
