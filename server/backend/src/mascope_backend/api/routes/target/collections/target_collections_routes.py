from fastapi import APIRouter, BackgroundTasks, Query, Request, Depends
from mascope_backend.db.id import gen_id
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
    TargetCollectionCreateBody,
    TargetCollectionUpdateBody,
)

target_collections_router = APIRouter(
    prefix="/api/target/collections", tags=["Target Collections"]
)


@target_collections_router.get("")
@api_route()
async def get_target_collections_route(
    query_params: GetTargetCollectionsQueryParams = Depends(),
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
    request: Request,
    body: TargetCollectionCreateBody,
    background_tasks: BackgroundTasks,
    user=Depends(editor_user),
):
    """Create a new target collection.

    :param request: The request object.
    :param body: The data required to create a new target collection.
    :param background_tasks: Background tasks for processing related tasks asynchronously.
    :param user: The current authenticated user, with editor permissions.
    :return: A dictionary containing the created target collection and related logs.
    """
    sid = request.headers.get("X-SID")
    # generate process_id for the background task ramatch_batches
    process_id = gen_id(8)
    result = await create_target_collection(
        target_collection_create_body=body,
        background_tasks=background_tasks,
        sid=sid,
        process_id=process_id,
    )

    return {
        "data": result["data"],
        "message": result["message"],
        "message_logs": result["message_logs"],
        "process_id": process_id,
    }


@target_collections_router.patch("/{target_collection_id}")
@api_route()
async def update_target_collection_route(
    request: Request,
    target_collection_id: str,
    body: TargetCollectionUpdateBody,
    background_tasks: BackgroundTasks,
    user=Depends(editor_user),
):
    """Update an existing target collection.

    :param request: The request object.
    :param target_collection_id: The unique identifier of the target collection to update.
    :param body: The data required to update the target collection.
    :param background_tasks: Background tasks for processing related tasks asynchronously.
    :param user: The current authenticated user, with editor permissions.
    :return: A dictionary containing the updated target collection and related logs.
    """
    sid = request.headers.get("X-SID")
    # generate process_id for the background task ramatch_batches
    process_id = gen_id(8)
    result = await update_target_collection(
        target_collection_id=target_collection_id,
        target_collection_update_body=body,
        background_tasks=background_tasks,
        sid=sid,
        process_id=process_id,
    )

    return {
        "data": result["data"],
        "message": result["message"],
        "message_logs": result["message_logs"],
        "process_id": process_id,
    }


@target_collections_router.delete("/{target_collection_id}")
@api_route()
async def delete_target_collection_route(
    request: Request,
    target_collection_id: str,
    background_tasks: BackgroundTasks,
    delete_orphan_compounds: bool = Query(
        False,
        description="Delete orphan compounds associated with the target collection",
    ),
    user=Depends(editor_user),
):
    """Delete a specific target collection by ID.

    :param request: The request object.
    :param target_collection_id: The unique identifier of the target collection to delete.
    :param background_tasks: Background tasks for processing related tasks asynchronously.
    :param delete_orphan_compounds: Boolean flag to delete orphan compounds associated with the collection.
    :param user: The current authenticated user, with editor permissions.
    :return: A dictionary confirming deletion and providing related logs.
    """
    sid = request.headers.get("X-SID")
    # generate process_id for the background task ramatch_batches
    process_id = gen_id(8)
    result = await delete_target_collection(
        target_collection_id=target_collection_id,
        delete_orphan_compounds=delete_orphan_compounds,
        background_tasks=background_tasks,
        sid=sid,
        process_id=process_id,
    )
    return {
        "message": result["message"],
        "message_logs": result["message_logs"],
        "process_id": process_id,
    }
