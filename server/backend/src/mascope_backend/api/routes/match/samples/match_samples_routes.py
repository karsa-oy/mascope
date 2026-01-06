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
from mascope_backend.api.new.auth.dependencies import editor_user, guest_user


match_samples_router = APIRouter(prefix="/api/match/samples", tags=["Match Samples"])


@match_samples_router.get("")
@api_route()
async def get_match_samples_route(
    query_params: GetMatchSamplesQueryParams = Depends(),
    user=Depends(guest_user),
):
    """Retrieve a list of match samples based on query parameters.

    :param query_params: Query parameters for filtering and pagination.
    :type query_params: GetMatchSamplesQueryParams
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: A dictionary containing total count and list of match samples.
    :rtype: dict
    """
    return await get_match_samples(**query_params.model_dump())


@match_samples_router.get("/{match_sample_id}")
@api_route()
async def get_match_sample_route(
    match_sample_id: str,
    user=Depends(guest_user),
):
    """Retrieve details of a specific match sample by ID.

    :param match_sample_id: The unique identifier of the match sample.
    :type match_sample_id: str
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: A dictionary containing the match sample details.
    :rtype: dict
    """
    return await get_match_sample(match_sample_id)


@match_samples_router.post("")
@api_route(status_code=201)
async def create_match_samples_route(
    body: List[MatchSampleBase],
    user=Depends(editor_user),
):
    """Create new match samples.

    :param body: A list of match sample data for creation.
    :type body: List[MatchSampleBase]
    :param user: The current authenticated user with editor permissions.
    :type user: User
    :return: A dictionary containing the created match samples and messages.
    :rtype: dict
    """
    return await create_match_samples(match_samples=body, independent_transaction=True)


@match_samples_router.delete("")
@api_route()
async def delete_match_samples_route(
    body: FilterSamplePayload,
    user=Depends(editor_user),
):
    """Delete specific match samples based on sample item or batch.

    :param body: Data payload specifying sample item or batch IDs.
    :type body: FilterSamplePayload
    :param user: The current authenticated user with editor permissions.
    :type user: User
    :return: A dictionary confirming the deletion outcome.
    :rtype: dict
    """
    return await delete_match_samples(
        sample_item_id=body.sample_item_id,
        sample_batch_id=body.sample_batch_id,
    )
