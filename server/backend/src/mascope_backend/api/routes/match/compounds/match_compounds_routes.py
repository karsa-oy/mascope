from typing import List
from fastapi import APIRouter, Depends
from mascope_backend.api.lib.api_features import api_route
from mascope_backend.api.controllers.match.compounds.match_compounds_controller import (
    get_match_compounds,
    get_match_compound,
    create_match_compounds,
    delete_match_compounds,
)
from mascope_backend.api.models.match.compounds.match_compound_pydantic_model import (
    MatchCompoundBase,
    GetMatchCompoundsQueryParams,
    DeleteMatchCompounsPayload,
)
from mascope_backend.api.new.auth.dependencies import editor_user, guest_user

match_compounds_router = APIRouter(
    prefix="/api/match/compounds", tags=["Match Compounds"]
)


@match_compounds_router.get("")
@api_route()
async def get_all_match_compounds_route(
    query_params: GetMatchCompoundsQueryParams = Depends(),
    user=Depends(guest_user),
):
    """Retrieve a list of match compounds based on query parameters.

    :param query_params: Query parameters for filtering, deduplication, and pagination.
    :type query_params: GetMatchCompoundsQueryParams
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: A dictionary containing the total count and list of match compounds.
    :rtype: dict
    """
    return await get_match_compounds(**query_params.model_dump())


@match_compounds_router.get("/{match_compound_id}")
@api_route()
async def get_match_compound_route(
    match_compound_id: str,
    user=Depends(guest_user),
):
    """Retrieve details of a specific match compound by ID.

    :param match_compound_id: The unique identifier of the match compound.
    :type match_compound_id: str
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: A dictionary containing the match compound details.
    :rtype: dict
    """
    return await get_match_compound(match_compound_id)


@match_compounds_router.post("")
@api_route(status_code=201)
async def create_match_compounds_route(
    body: List[MatchCompoundBase],
    user=Depends(editor_user),
):
    """Create new match compounds.

    :param body: A list of match compound data for creation.
    :type body: List[MatchCompoundBase]
    :param user: The current authenticated user with editor permissions.
    :type user: User
    :return: A dictionary containing created match compounds and messages.
    :rtype: dict
    """
    return await create_match_compounds(
        match_compounds=body, independent_transaction=True
    )


@match_compounds_router.delete("")
@api_route()
async def delete_match_compounds_route(
    body: DeleteMatchCompounsPayload,
    user=Depends(editor_user),
):
    """Delete specific match compounds based on sample item or batch.

    :param body: Data payload specifying sample item, batch, and compound IDs.
    :type body: DeleteMatchCompounsPayload
    :param user: The current authenticated user with editor permissions.
    :type user: User
    :return: A dictionary confirming the deletion outcome.
    :rtype: dict
    """
    return await delete_match_compounds(
        sample_item_id=body.sample_item_id,
        sample_batch_id=body.sample_batch_id,
        target_compound_ids=body.target_compound_ids,
    )
