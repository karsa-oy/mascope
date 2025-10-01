"""
Match records API routes for retrieving target collections and ions with match data.

Provides endpoints for loading match records at collection and ion levels,
supporting both sample-specific and batch-level queries with optional filtering.
"""

from fastapi import APIRouter, Depends, Query

from mascope_backend.db.models import User
from mascope_backend.api.lib.api_features import api_route
from mascope_backend.api.new.auth.dependencies import guest_user
from mascope_backend.api.new.match.records import (
    get_match_collection_records,
    get_match_ion_records,
    get_match_isotope_records,
    get_batch_overview_match_records,
)
from mascope_backend.api.new.match.records.schemas import (
    MatchRecordsQueryParams,
    MatchIonRecordsQueryParams,
    MatchIsotopeRecordsQueryParams,
    MatchRecordsBatchOverviewQueryParams,
    MatchRecordsResponse,
)


match_records_router = APIRouter(prefix="/api/match/records", tags=["Match Records"])


@match_records_router.get("/collection", response_model=MatchRecordsResponse)
@api_route()
async def get_match_collection_records_route(
    query_params: MatchRecordsQueryParams = Query(), user: User = Depends(guest_user)
) -> MatchRecordsResponse:
    """
    Retrieve target collections with match collection data.

    Supports both sample-level (actual match data) and batch-level (placeholder data) queries.

    :param query_params: Query parameters including sample/batch IDs and optional filters
    :type query_params: MatchRecordsQueryParams
    :param user: Authenticated user with guest permissions
    :type user: User
    :return: Target collections with match data
    :rtype: MatchRecordsResponse
    """
    result = await get_match_collection_records(**query_params.model_dump())
    return MatchRecordsResponse.model_validate(result)


@match_records_router.get("/ion", response_model=MatchRecordsResponse)
@api_route()
async def get_match_ion_records_route(
    query_params: MatchIonRecordsQueryParams = Query(), user: User = Depends(guest_user)
) -> MatchRecordsResponse:
    """
    Retrieve target ions with match ion data.

    Supports both sample-level and batch-level queries with optional target collection filtering.
    Returns target compound and target ion data with nested match ion information.

    :param query_params: Query parameters including sample/batch IDs and optional filters
    :type query_params: MatchIonRecordsQueryParams
    :param user: Authenticated user with guest permissions
    :type user: User
    :return: Target ions with match data
    :rtype: MatchRecordsResponse
    """
    result = await get_match_ion_records(**query_params.model_dump())
    return MatchRecordsResponse.model_validate(result)


@match_records_router.get("/isotope", response_model=MatchRecordsResponse)
@api_route()
async def get_match_isotopes_records_route(
    query_params: MatchIsotopeRecordsQueryParams = Query(),
    user: User = Depends(guest_user),
) -> MatchRecordsResponse:
    """
    Retrieve target isotopes with match isotope data.

    Supports both sample-level and batch-level queries with optional filtering
    by target collection and target ion.

    Returns target compound, target ion, and target isotope data with
    nested match isotope information.

    :param query_params: Query parameters including sample/batch IDs and optional filters
    :type query_params: MatchIsotopeRecordsQueryParams
    :param user: Authenticated user with guest permissions
    :type user: User
    :return: Target isotopes with match data
    :rtype: MatchRecordsResponse
    """
    result = await get_match_isotope_records(**query_params.model_dump())
    return MatchRecordsResponse.model_validate(result)


@match_records_router.get("/batch_overview", response_model=MatchRecordsResponse)
@api_route()
async def get_batch_overview_match_records_route(
    query_params: MatchRecordsBatchOverviewQueryParams = Query(),
    user: User = Depends(guest_user),
) -> MatchRecordsResponse:
    """
    Retrieve batch overview records for chart visualization.

    Returns flattened match records optimized for trace building.
    Only includes valid matches (match_category > 0) for selected batch and collection.

    Designed specifically for ChartBatchOverview component - minimal data,
    pre-joined, ready for grouping by target_ion_id.

    :param query_params: Query parameters including batch ID and target collection ID filter
    :type query_params: MatchRecordsBatchOverviewQueryParams
    :param user: Authenticated user with guest permissions
    :type user: User
    :return: Flattened batch overview records
    :rtype: MatchRecordsResponse
    """
    result = await get_batch_overview_match_records(**query_params.model_dump())
    return MatchRecordsResponse.model_validate(result)
