from typing import List

from fastapi import APIRouter, Depends

from mascope_backend.api.controllers.match.collections.match_collections_controller import (
    create_match_collections,
    delete_match_collections,
    get_match_collection,
    get_match_collections,
)
from mascope_backend.api.lib.api_features import api_route
from mascope_backend.api.models.match.collections.match_collection_pydantic_model import (
    DeleteMatchCollectionsPayload,
    GetMatchCollectionsQueryParams,
    MatchCollectionBase,
)
from mascope_backend.api.new.auth.dependencies import current_active_user
from mascope_backend.api.new.workspaces.dependencies import (
    check_batch_access,
    check_sample_access,
    check_sample_access_bulk,
)
from mascope_backend.db import User


match_collections_router = APIRouter(
    prefix="/api/match/collections", tags=["Match Collections"]
)


@match_collections_router.get("")
@api_route()
async def get_match_collections_route(
    query_params: GetMatchCollectionsQueryParams = Depends(),
    user: User = Depends(current_active_user),
):
    """Retrieve a list of match collections based on query parameters.

    :param query_params: Query parameters for filtering and pagination.
    :type query_params: GetMatchCollectionsQueryParams
    :param user: The current authenticated user. Requires workspace guest role.
    :type user: User
    :return: A dictionary containing total count and list of match collections.
    :rtype: dict
    """
    if query_params.sample_item_id:
        await check_sample_access(query_params.sample_item_id, user, "guest")
    elif query_params.sample_batch_id:
        await check_batch_access(query_params.sample_batch_id, user, "guest")
    else:
        raise ValueError("Either sample_item_id or sample_batch_id must be provided.")
    return await get_match_collections(**query_params.model_dump())


@match_collections_router.get("/{match_collection_id}")
@api_route()
async def get_match_collection_route(
    match_collection_id: str,
    user: User = Depends(current_active_user),
):
    """Retrieve details of a specific match collection by ID.

    :param match_collection_id: The unique identifier of the match collection.
    :type match_collection_id: str
    :param user: The current authenticated user. Requires workspace guest role.
    :type user: User
    :return: A dictionary containing the match collection details.
    :rtype: dict
    """
    result = await get_match_collection(match_collection_id)
    await check_sample_access(result["data"]["sample_item_id"], user, "guest")
    return result


@match_collections_router.post("")
@api_route(status_code=201)
async def create_match_collections_route(
    body: List[MatchCollectionBase],
    user: User = Depends(current_active_user),
):
    """Create new match collections.

    :param body: A list of match collection data for creation.
    :type body: List[MatchCollectionBase]
    :param user: The current authenticated user. Requires workspace editor role.
    :type user: User
    :return: A dictionary containing the created match collections and messages.
    :rtype: dict
    """
    sample_ids = list({item.sample_item_id for item in body})
    await check_sample_access_bulk(sample_ids, user, "editor")
    return await create_match_collections(
        match_collections=body, independent_transaction=True
    )


@match_collections_router.delete("")
@api_route()
async def delete_match_collections_route(
    body: DeleteMatchCollectionsPayload,
    user: User = Depends(current_active_user),
):
    """Delete specific match collections based on sample item or batch.

    :param body: Data payload specifying sample item, batch, and collection IDs.
    :type body: DeleteMatchCollectionsPayload
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
    return await delete_match_collections(
        sample_item_id=body.sample_item_id,
        sample_batch_id=body.sample_batch_id,
        target_collections_ids=body.target_collections_ids,
    )
