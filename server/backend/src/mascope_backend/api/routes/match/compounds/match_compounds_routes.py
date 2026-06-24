from typing import List

from fastapi import APIRouter, Depends

from mascope_backend.api.controllers.match.compounds.match_compounds_controller import (
    create_match_compounds,
    delete_match_compounds,
    get_match_compound,
    get_match_compounds,
)
from mascope_backend.api.lib.api_features import api_route
from mascope_backend.api.models.match.compounds.match_compound_pydantic_model import (
    DeleteMatchCompoundsPayload,
    GetMatchCompoundsQueryParams,
    MatchCompoundBase,
)
from mascope_backend.api.new.auth.dependencies import current_active_user
from mascope_backend.api.new.workspaces.dependencies import (
    check_batch_access,
    check_sample_access,
    check_sample_access_bulk,
)
from mascope_backend.db import User


match_compounds_router = APIRouter(
    prefix="/api/match/compounds", tags=["Match Compounds"]
)


@match_compounds_router.get("")
@api_route()
async def get_all_match_compounds_route(
    query_params: GetMatchCompoundsQueryParams = Depends(),
    user: User = Depends(current_active_user),
):
    """Retrieve a list of match compounds based on query parameters.

    :param query_params: Query parameters for filtering, deduplication, and pagination.
    :type query_params: GetMatchCompoundsQueryParams
    :param user: The current authenticated user. Requires workspace guest role.
    :type user: User
    :return: A dictionary containing the total count and list of match compounds.
    :rtype: dict
    """
    if query_params.sample_item_id:
        await check_sample_access(query_params.sample_item_id, user, "guest")
    elif query_params.sample_batch_id:
        await check_batch_access(query_params.sample_batch_id, user, "guest")
    else:
        raise ValueError("Either sample_item_id or sample_batch_id must be provided.")
    return await get_match_compounds(**query_params.model_dump())


@match_compounds_router.get("/{match_compound_id}")
@api_route()
async def get_match_compound_route(
    match_compound_id: str,
    user: User = Depends(current_active_user),
):
    """Retrieve details of a specific match compound by ID.

    :param match_compound_id: The unique identifier of the match compound.
    :type match_compound_id: str
    :param user: The current authenticated user. Requires workspace guest role.
    :type user: User
    :return: A dictionary containing the match compound details.
    :rtype: dict
    """
    result = await get_match_compound(match_compound_id)
    await check_sample_access(result["data"]["sample_item_id"], user, "guest")
    return result


@match_compounds_router.post("")
@api_route(status_code=201)
async def create_match_compounds_route(
    body: List[MatchCompoundBase],
    user: User = Depends(current_active_user),
):
    """Create new match compounds.

    :param body: A list of match compound data for creation.
    :type body: List[MatchCompoundBase]
    :param user: The current authenticated user. Requires workspace editor role.
    :type user: User
    :return: A dictionary containing created match compounds and messages.
    :rtype: dict
    """
    sample_ids = list({item.sample_item_id for item in body})
    await check_sample_access_bulk(sample_ids, user, "editor")
    return await create_match_compounds(
        match_compounds=body, independent_transaction=True
    )


@match_compounds_router.delete("")
@api_route()
async def delete_match_compounds_route(
    body: DeleteMatchCompoundsPayload,
    user: User = Depends(current_active_user),
):
    """Delete specific match compounds based on sample item or batch.

    :param body: Data payload specifying sample item, batch, and compound IDs.
    :type body: DeleteMatchCompoundsPayload
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
    return await delete_match_compounds(
        sample_item_id=body.sample_item_id,
        sample_batch_id=body.sample_batch_id,
        target_compound_ids=body.target_compound_ids,
    )
