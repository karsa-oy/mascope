"""
Match records API routes for retrieving target collections and ions with match data.

Provides endpoints for loading match records at collection and ion levels,
supporting both sample-specific and batch-level queries with optional filtering.
"""

from fastapi import APIRouter, Depends, Query, Path

from mascope_backend.db.models import User
from mascope_backend.api.lib.api_features import api_route
from mascope_backend.api.lib.exceptions.api_exceptions import (
    NotFoundException,
)
from mascope_backend.api.new.auth.dependencies import guest_user
from mascope_backend.api.new.match.records import (
    get_match_collection_records,
    get_match_ion_records,
    get_match_isotope_records,
)
from mascope_backend.api.new.match.records.schemas import (
    MatchRecordsQueryParams,
    MatchIonRecordsBody,
    MatchIsotopeRecordsQueryParams,
    MatchRecordsResponse,
    MatchRecordsSingleResponse,
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


@match_records_router.get(
    "/collection/{target_collection_id}", response_model=MatchRecordsSingleResponse
)
@api_route()
async def get_match_collection_record_route(
    target_collection_id: str = Path(..., description="Target collection ID"),
    query_params: MatchRecordsQueryParams = Query(),
    user: User = Depends(guest_user),
) -> MatchRecordsSingleResponse:
    """
    Retrieve a single target collection with match collection data by ID.

    Supports both sample-level (actual match data) and batch-level (placeholder data) queries.
    Returns 404 if collection not found in the specified sample/batch.

    :param target_collection_id: Target collection ID to retrieve
    :type target_collection_id: str
    :param query_params: Query parameters including sample/batch IDs
    :type query_params: MatchRecordsQueryParams
    :param user: Authenticated user with guest permissions
    :type user: User
    :return: Single target collection with match data
    :rtype: MatchRecordsSingleResponse
    """
    result = await get_match_collection_records(
        target_collection_id=target_collection_id, **query_params.model_dump()
    )

    if not result["data"]:
        entity_type = "sample" if query_params.sample_item_id else "batch"
        entity_id = query_params.sample_item_id or query_params.sample_batch_id
        raise NotFoundException(
            f"Collection '{target_collection_id}' not found for {entity_type} '{entity_id}'"
        )

    # Extract single record from list
    single_record = result["data"][0]

    return MatchRecordsSingleResponse(
        status=result["status"], message=result["message"], data=single_record
    )


@match_records_router.post("/ion", response_model=MatchRecordsResponse)
@api_route()
async def get_match_ion_records_route(
    body: MatchIonRecordsBody, user: User = Depends(guest_user)
) -> MatchRecordsResponse:
    """
    Retrieve target ions with match ion data.

    Supports both sample-level and batch-level queries with optional target collection filtering.
    Returns target compound and target ion data with nested match ion information.

    :param body: Request body including sample/batch IDs and optional filters
    :type body: MatchIonRecordsBody
    :param user: Authenticated user with guest permissions
    :type user: User
    :return: Target ions with match data
    :rtype: MatchRecordsResponse
    """
    result = await get_match_ion_records(**body.model_dump())
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
