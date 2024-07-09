from fastapi import APIRouter, Depends
from mascope_server.api.utils.api_features import api_route
from mascope_server.api.controllers.match.batch.match_batch_targets_controller import (
    get_match_batch_collections,
    get_match_batch_compounds,
    get_match_batch_ions,
    get_match_batch_isotopes,
)
from mascope_server.api.models.pydantic_models.match.batch.match_batch_targets_pydantic_model import (
    SortingPaginationQueryParams,
    GetMatchBatchCompoundsQueryParams,
    GetMatchBatchIonsQueryParams,
    GetMatchBatchIsotopesQueryParams,
)

match_batch_targets_router = APIRouter()


@match_batch_targets_router.get(
    "/api/match/batch/{sample_batch_id}/collections", tags=["Batch Match Loading"]
)
@api_route()
async def get_match_batch_collections_route(
    sample_batch_id: str,
    query_params: SortingPaginationQueryParams = Depends(),
):
    return await get_match_batch_collections(
        sample_batch_id=sample_batch_id, **query_params.dict()
    )


@match_batch_targets_router.get(
    "/api/match/batch/{sample_batch_id}/compounds", tags=["Batch Match Loading"]
)
@api_route()
async def get_match_batch_compounds_route(
    sample_batch_id: str,
    query_params: GetMatchBatchCompoundsQueryParams = Depends(),
):
    return await get_match_batch_compounds(
        sample_batch_id=sample_batch_id, **query_params.dict()
    )


@match_batch_targets_router.get(
    "/api/match/batch/{sample_batch_id}/ions", tags=["Batch Match Loading"]
)
@api_route()
async def get_match_batch_ions_route(
    sample_batch_id: str,
    query_params: GetMatchBatchIonsQueryParams = Depends(),
):
    return await get_match_batch_ions(
        sample_batch_id=sample_batch_id, **query_params.dict()
    )


@match_batch_targets_router.get(
    "/api/match/batch/{sample_batch_id}/isotopes", tags=["Batch Match Loading"]
)
@api_route()
async def get_match_batch_isotopes_route(
    sample_batch_id: str,
    query_params: GetMatchBatchIsotopesQueryParams = Depends(),
):
    return await get_match_batch_isotopes(
        sample_batch_id=sample_batch_id, **query_params.dict()
    )
