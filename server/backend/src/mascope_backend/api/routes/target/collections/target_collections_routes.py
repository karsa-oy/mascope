from fastapi import APIRouter, Query, Depends
from mascope_backend.api.new.auth.dependencies import editor_user, guest_user
from mascope_backend.api.lib.api_features import api_route
from mascope_backend.api.controllers.target.collections.target_collections_controller import (
    get_target_collections,
    get_target_collection,
    create_target_collection,
    delete_target_collection,
    update_target_collection,
)
from mascope_backend.api.models.target.collections.target_collection_pydantic_model import (
    GetTargetCollectionsQueryParams,
    TargetCollectionCreate,
    TargetCollectionUpdate,
)

target_collections_router = APIRouter(
    prefix="/api/target/collections", tags=["Target Collections"]
)


@target_collections_router.get("")
@api_route()
async def get_target_collections_route(
    query_params: GetTargetCollectionsQueryParams = Query(),
    user=Depends(guest_user),
):
    """Retrieve a list of target collections.

    :param query_params: Query parameters for filtering, sorting, and pagination.
    :param user: The current authenticated user, with guest permissions.
    :return: A dictionary containing the total count and list of target collections.
    """
    return await get_target_collections(**query_params.model_dump())


@target_collections_router.get("/{target_collection_id}")
@api_route()
async def get_target_collection_route(
    target_collection_id: str,
    user=Depends(guest_user),
):
    """Retrieve details of a specific target collection by ID.

    :param target_collection_id: The unique identifier of the target collection.
    :param user: The current authenticated user, with guest permissions.
    :return: A dictionary containing the target collection details.
    """
    return await get_target_collection(target_collection_id)


@target_collections_router.post("")
@api_route(status_code=201)
async def create_target_collection_route(
    body: TargetCollectionCreate,
    user=Depends(editor_user),
) -> dict:
    """Create a new target collection.

    :param body: The data required to create a new target collection.
    :type body: TargetCollectionCreate
    :param user: The current authenticated user, with editor permissions.
    :type user: User
    :return: A dictionary containing the created target collection and related message, status.
    :rtype: dict
    """
    return await create_target_collection(
        target_collection_create=body,
        independent_transaction=True,
    )


@target_collections_router.patch("/{target_collection_id}")
@api_route()
async def update_target_collection_route(
    target_collection_id: str,
    body: TargetCollectionUpdate,
    user=Depends(editor_user),
) -> dict:
    """Update an existing target collection.

    :param target_collection_id: The unique identifier of the target collection to update.
    :type target_collection_id: str
    :param body: The data required to update the target collection.
    :type body: TargetCollectionUpdate
    :param user: The current authenticated user with editor permissions.
    :type user: User
    :return: Update results details
    :rtype: dict
    """
    return await update_target_collection(
        target_collection_id=target_collection_id,
        target_collection_update=body,
        independent_transaction=True,
    )


@target_collections_router.delete("/{target_collection_id}")
@api_route()
async def delete_target_collection_route(
    target_collection_id: str,
    delete_orphan_compounds: bool = Query(
        False,
        description="Delete orphan compounds associated with the target collection",
    ),
    user=Depends(editor_user),
) -> dict:
    """Delete a specific target collection by ID.

    :param target_collection_id: The unique identifier of the target collection to delete.
    :type target_collection_id: str
    :param delete_orphan_compounds: Boolean flag to delete orphan compounds associated with the collection.
    :type delete_orphan_compounds: bool
    :param user: The current authenticated user, with editor permissions.
    :type user: User
    :return: A dictionary confirming deletion and providing related logs.
    :rtype: dict
    """
    return await delete_target_collection(
        target_collection_id=target_collection_id,
        delete_orphan_compounds=delete_orphan_compounds,
        independent_transaction=True,
    )
