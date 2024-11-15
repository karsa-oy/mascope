from typing import List
from fastapi import APIRouter, Depends
from mascope_server.api.lib.api_features import api_route
from mascope_server.api.controllers.match.collections.match_collections_controller import (
    get_match_collections,
    get_match_collection,
    create_match_collections,
    delete_match_collections,
)
from mascope_server.api.models.match.collections.match_collection_pydantic_model import (
    MatchCollectionBase,
    GetMatchCollectionsQueryParams,
    DeleteMatchCollectionsPayload,
)
from mascope_server.api.new.auth.dependencies import editor_user, guest_user

match_collections_router = APIRouter(
    prefix="/api/match/collections", tags=["Match Collections"]
)


@match_collections_router.get("")
@api_route()
async def get_match_collections_route(
    query_params: GetMatchCollectionsQueryParams = Depends(),
    user=Depends(guest_user),
):
    """Retrieve a list of match collections based on query parameters.

    :param query_params: Query parameters for filtering and pagination.
    :type query_params: GetMatchCollectionsQueryParams
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: A dictionary containing total count and list of match collections.
    :rtype: dict
    """
    return await get_match_collections(**query_params.model_dump())


@match_collections_router.get("/{match_collection_id}")
@api_route()
async def get_match_collection_route(
    match_collection_id: str,
    user=Depends(guest_user),
):
    """Retrieve details of a specific match collection by ID.

    :param match_collection_id: The unique identifier of the match collection.
    :type match_collection_id: str
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: A dictionary containing the match collection details.
    :rtype: dict
    """
    return await get_match_collection(match_collection_id)


@match_collections_router.post("")
@api_route(status_code=201)
async def create_match_collections_route(
    body: List[MatchCollectionBase],
    user=Depends(editor_user),
):
    """Create new match collections.

    :param body: A list of match collection data for creation.
    :type body: List[MatchCollectionBase]
    :param user: The current authenticated user with editor permissions.
    :type user: User
    :return: A dictionary containing the created match collections and messages.
    :rtype: dict
    """
    return await create_match_collections(
        match_collections=body, independent_transaction=True
    )


@match_collections_router.delete("")
@api_route()
async def delete_match_collections_route(
    body: DeleteMatchCollectionsPayload,
    user=Depends(editor_user),
):
    """Delete specific match collections based on sample item or batch.

    :param body: Data payload specifying sample item, batch, and collection IDs.
    :type body: DeleteMatchCollectionsPayload
    :param user: The current authenticated user with editor permissions.
    :type user: User
    :return: A dictionary confirming the deletion outcome.
    :rtype: dict
    """
    return await delete_match_collections(
        sample_item_id=body.sample_item_id,
        sample_batch_id=body.sample_batch_id,
        target_collections_ids=body.target_collections_ids,
    )
