from typing import List

from fastapi import APIRouter, Depends

from mascope_backend.api.controllers.match.samples.match_samples_controller import (
    create_match_samples,
    delete_match_samples,
    get_match_sample,
    get_match_samples,
)
from mascope_backend.api.lib.api_features import api_route
from mascope_backend.api.models.match.match_pydantic_model import FilterSamplePayload
from mascope_backend.api.models.match.samples.match_sample_pydantic_model import (
    GetMatchSamplesQueryParams,
    MatchSampleBase,
)
from mascope_backend.api.new.auth.dependencies import current_active_user
from mascope_backend.api.new.workspaces.dependencies import (
    check_batch_access,
    check_sample_access,
    check_sample_access_bulk,
)
from mascope_backend.db import User


match_samples_router = APIRouter(prefix="/api/match/samples", tags=["Match Samples"])


@match_samples_router.get("")
@api_route()
async def get_match_samples_route(
    query_params: GetMatchSamplesQueryParams = Depends(),
    user: User = Depends(current_active_user),
):
    """Retrieve a list of match samples based on query parameters.

    :param query_params: Query parameters for filtering and pagination.
    :type query_params: GetMatchSamplesQueryParams
    :param user: The current authenticated user. Requires workspace guest role.
    :type user: User
    :return: A dictionary containing total count and list of match samples.
    :rtype: dict
    """
    if query_params.sample_item_id:
        await check_sample_access(query_params.sample_item_id, user, "guest")
    elif query_params.sample_batch_id:
        await check_batch_access(query_params.sample_batch_id, user, "guest")
    else:
        raise ValueError("Either sample_item_id or sample_batch_id must be provided.")
    return await get_match_samples(**query_params.model_dump())


@match_samples_router.get("/{match_sample_id}")
@api_route()
async def get_match_sample_route(
    match_sample_id: str,
    user: User = Depends(current_active_user),
):
    """Retrieve details of a specific match sample by ID.

    :param match_sample_id: The unique identifier of the match sample.
    :type match_sample_id: str
    :param user: The current authenticated user. Requires workspace guest role.
    :type user: User
    :return: A dictionary containing the match sample details.
    :rtype: dict
    """
    result = await get_match_sample(match_sample_id)
    await check_sample_access(result["data"]["sample_item_id"], user, "guest")
    return result


@match_samples_router.post("")
@api_route(status_code=201)
async def create_match_samples_route(
    body: List[MatchSampleBase],
    user: User = Depends(current_active_user),
):
    """Create new match samples.

    :param body: A list of match sample data for creation.
    :type body: List[MatchSampleBase]
    :param user: The current authenticated user. Requires workspace editor role.
    :type user: User
    :return: A dictionary containing the created match samples and messages.
    :rtype: dict
    """
    sample_ids = list({item.sample_item_id for item in body})
    await check_sample_access_bulk(sample_ids, user, "editor")
    return await create_match_samples(match_samples=body, independent_transaction=True)


@match_samples_router.delete("")
@api_route()
async def delete_match_samples_route(
    body: FilterSamplePayload,
    user: User = Depends(current_active_user),
):
    """Delete specific match samples based on sample item or batch.

    :param body: Data payload specifying sample item or batch IDs.
    :type body: FilterSamplePayload
    :param user: The current authenticated user. Requires workspace editor role.
    :type user: User
    :return: A dictionary confirming the deletion outcome.
    :rtype: dict
    """
    if body.sample_item_id:
        await check_sample_access(body.sample_item_id, user, "editor")
    elif body.sample_batch_id:
        await check_batch_access(body.sample_batch_id, user, "editor")
    else:
        raise ValueError("Either sample_item_id or sample_batch_id must be provided.")
    return await delete_match_samples(
        sample_item_id=body.sample_item_id,
        sample_batch_id=body.sample_batch_id,
    )
