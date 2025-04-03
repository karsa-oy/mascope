from typing import List
from fastapi import APIRouter, Depends
from mascope_backend.api.new.auth.dependencies import guest_user, editor_user
from mascope_backend.api.lib.api_features import api_route
from mascope_backend.api.controllers.match.ions.match_ions_controller import (
    get_match_ions,
    get_match_ion,
    create_match_ions,
    delete_match_ions,
)
from mascope_backend.api.models.match.ions.match_ion_pydantic_model import (
    MatchIonBase,
    GetMatchIonsQueryParams,
    DeleteMatchIonsPayload,
)

match_ions_router = APIRouter(prefix="/api/match/ions", tags=["Match Ions"])


@match_ions_router.get("")
@api_route()
async def get_match_ions_route(
    query_params: GetMatchIonsQueryParams = Depends(),
    user=Depends(guest_user),
):
    """Retrieve a list of matched ions based on query parameters.

    :param query_params: Query parameters for filtering, sorting, and pagination.
    :type query_params: GetMatchIonsQueryParams
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: A dictionary containing total count and list of matched ions.
    :rtype: dict
    """
    return await get_match_ions(**query_params.model_dump())


@match_ions_router.get("/{match_ion_id}")
@api_route()
async def get_match_ion_route(
    match_ion_id: str,
    user=Depends(guest_user),
):
    """Retrieve details of a specific match ion by ID.

    :param match_ion_id: The unique identifier of the match ion.
    :type match_ion_id: str
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: A dictionary containing the match ion details.
    :rtype: dict
    """
    return await get_match_ion(match_ion_id)


@match_ions_router.post("")
@api_route(status_code=201)
async def create_match_ions_route(
    body: List[MatchIonBase],
    user=Depends(editor_user),
):
    """Create new match ions.

    :param body: A list of match ion data for creation.
    :type body: List[MatchIonBase]
    :param user: The current authenticated user with editor permissions.
    :type user: User
    :return: A dictionary containing the created match ions and messages.
    :rtype: dict
    """
    return await create_match_ions(match_ions=body, independent_transaction=True)


@match_ions_router.delete("")
@api_route()
async def delete_match_ions_route(
    body: DeleteMatchIonsPayload,
    user=Depends(editor_user),
):
    """Delete specific match ions based on sample item or batch.

    :param body: Data payload specifying sample item, batch, and ion IDs.
    :type body: DeleteMatchIonsPayload
    :param user: The current authenticated user with editor permissions.
    :type user: User
    :return: A dictionary confirming the deletion outcome.
    :rtype: dict
    """
    return await delete_match_ions(
        sample_item_id=body.sample_item_id,
        sample_batch_id=body.sample_batch_id,
        target_ion_ids=body.target_ion_ids,
    )
