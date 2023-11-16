from fastapi import APIRouter, Query, BackgroundTasks
from ..controllers.target_collections_controller import (
    get_target_collection_by_id,
    get_target_collections,
    create_target_collection,
    delete_target_collection,
    update_target_collection,
)
from ..models.pydantic_models.target_collection_pydantic_model import (
    TargetCollectionCreate,
    TargetCollectionUpdate,
)


target_collections_router = APIRouter()


@target_collections_router.get("/api/target_collections")
async def get_target_collections_route(
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 100,
):
    return await get_target_collections(sort, order, page, limit)


@target_collections_router.get("/api/target_collections/{target_collection_id}")
async def get_target_collection_by_id_route(target_collection_id: str):
    return await get_target_collection_by_id(target_collection_id)


@target_collections_router.post("/api/target_collections")
async def create_target_collection_route(
    target_collection: TargetCollectionCreate, background_tasks: BackgroundTasks
):
    result = await create_target_collection(target_collection, background_tasks)
    response = {
        "new_target_collection": result["new_target_collection"],
        "created_compounds_count": result["created_compounds_count"],
        "created_compounds": result["created_compounds"],
        "existing_compounds_count": result["existing_compounds_count"],
        "existing_compounds": result["existing_compounds"],
        "message_logs": result["message_logs"],
    }
    return response


@target_collections_router.delete("/api/target_collections/{target_collection_id}")
async def delete_target_collection_route(
    target_collection_id: str,
    background_tasks: BackgroundTasks,
    delete_orphan_compounds: bool = Query(
        False,
        description="Delete orphan compounds associated with the target collection",
    ),
):
    return await delete_target_collection(
        target_collection_id, background_tasks, delete_orphan_compounds
    )


@target_collections_router.patch("/api/target_collections/{target_collection_id}")
async def update_target_collection_route(
    target_collection_id: str, target_collection_update: TargetCollectionUpdate
):
    response = await update_target_collection(
        target_collection_id, target_collection_update
    )

    return {
        "updated_target_collection": response["updated_target_collection"],
        "added_compounds": response["added_compounds"],
        "removed_compounds": response["removed_compounds"],
        "message_logs": response["message_logs"],
    }
