from typing import List
from fastapi import APIRouter, Depends
from mascope_server.api.lib.api_features import api_route
from mascope_server.api.controllers.match.interferences.match_interferences_controller import (
    get_match_interference,
    get_match_interferences,
    create_match_interferences,
    delete_match_interferences,
)
from mascope_server.api.models.match.interferences.match_interferences_pydantic_model import (
    MatchInterferenceBase,
    GetMatchInterferencesQueryParams,
    DeleteMatchInterferencesPayload,
)
from mascope_server.api.new.auth.dependencies import editor_user, guest_user

match_interferences_router = APIRouter(
    prefix="/api/match/interferences", tags=["Match Interferences"]
)


@match_interferences_router.get("")
@api_route()
async def get_match_interferences_route(
    query_params: GetMatchInterferencesQueryParams = Depends(),
    user=Depends(guest_user),
):
    """Retrieve a list of match interferences with filtering options.

    :param query_params: Query parameters for filtering and pagination.
    :type query_params: GetMatchInterferencesQueryParams
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: A dictionary containing total count and list of match interferences.
    :rtype: dict
    """
    return await get_match_interferences(**query_params.model_dump())


@match_interferences_router.get("/{match_interference_id}")
@api_route()
async def get_match_interference_route(
    match_interference_id: str,
    user=Depends(guest_user),
):
    """Retrieve details of a specific match interference by ID.

    :param match_interference_id: The unique identifier of the match interference.
    :type match_interference_id: str
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: A dictionary containing the match interference details.
    :rtype: dict
    """
    return await get_match_interference(match_interference_id)


@match_interferences_router.post("")
@api_route(status_code=201)
async def create_match_interferences_route(
    body: List[MatchInterferenceBase],
    user=Depends(editor_user),
):
    """Create new match interferences.

    :param body: A list of match interference data for creation.
    :type body: List[MatchInterferenceBase]
    :param user: The current authenticated user with editor permissions.
    :type user: User
    :return: A dictionary containing the created match interferences and messages.
    :rtype: dict
    """
    return await create_match_interferences(
        match_interferences=body, independent_transaction=True
    )


@match_interferences_router.delete("")
@api_route()
async def delete_match_interferences_route(
    body: DeleteMatchInterferencesPayload,
    user=Depends(editor_user),
):
    """Delete specific match interferences based on sample item or batch.

    :param body: Data payload specifying sample item, batch, and target isotope IDs.
    :type body: DeleteMatchInterferencesPayload
    :param user: The current authenticated user with editor permissions.
    :type user: User
    :return: A dictionary confirming the deletion outcome.
    :rtype: dict
    """
    return await delete_match_interferences(
        sample_item_id=body.sample_item_id,
        sample_batch_id=body.sample_batch_id,
        target_isotope_ids=body.target_isotope_ids,
    )
