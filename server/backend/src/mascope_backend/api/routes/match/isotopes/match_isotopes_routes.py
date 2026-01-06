from typing import List

from fastapi import APIRouter, Depends

from mascope_backend.api.controllers.match.isotopes.match_isotopes_controller import (
    create_match_isotopes,
    delete_match_isotopes,
    get_match_isotope,
    get_match_isotopes,
)
from mascope_backend.api.lib.api_features import api_route
from mascope_backend.api.models.match.isotopes.match_isotopes_pydantic_model import (
    DeleteMatchIsotopesPayload,
    GetMatchesQueryParams,
    MatchIsotopeBase,
)
from mascope_backend.api.new.auth.dependencies import editor_user, guest_user


match_isotopes_router = APIRouter(prefix="/api/match/isotopes", tags=["Match Isotopes"])


@match_isotopes_router.get("")
@api_route()
async def get_match_isotopes_route(
    query_params: GetMatchesQueryParams = Depends(),
    user=Depends(guest_user),
):
    """Retrieve a list of match isotopes based on query parameters.

    :param query_params: Query parameters for filtering and pagination.
    :type query_params: GetMatchesQueryParams
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: A dictionary containing total count and list of match isotopes.
    :rtype: dict
    """
    return await get_match_isotopes(**query_params.model_dump())


@match_isotopes_router.get("/{match_isotope_id}")
@api_route()
async def get_match_isotope_route(
    match_isotope_id: str,
    user=Depends(guest_user),
):
    """Retrieve details of a specific match isotope by ID.

    :param match_isotope_id: The unique identifier of the match isotope.
    :type match_isotope_id: str
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: A dictionary containing the match isotope details.
    :rtype: dict
    """
    return await get_match_isotope(match_isotope_id)


@match_isotopes_router.post("")
@api_route(status_code=201)
async def create_match_isotopes_route(
    body: List[MatchIsotopeBase],
    user=Depends(editor_user),
):
    """Create new match isotopes.

    :param body: A list of match isotope data for creation.
    :type body: List[MatchIsotopeBase]
    :param user: The current authenticated user with editor permissions.
    :type user: User
    :return: A dictionary containing the created match isotopes and messages.
    :rtype: dict
    """
    return await create_match_isotopes(
        match_isotopes=body, independent_transaction=True
    )


@match_isotopes_router.delete("")
@api_route()
async def delete_match_isotopes_route(
    body: DeleteMatchIsotopesPayload,
    user=Depends(editor_user),
):
    """Delete specific match isotopes based on sample item or batch.

    :param body: Data payload specifying sample item, batch, and isotope IDs.
    :type body: DeleteMatchIsotopesPayload
    :param user: The current authenticated user with editor permissions.
    :type user: User
    :return: A dictionary confirming the deletion outcome.
    :rtype: dict
    """
    return await delete_match_isotopes(
        sample_item_id=body.sample_item_id,
        sample_batch_id=body.sample_batch_id,
        target_isotope_ids=body.target_isotope_ids,
    )
