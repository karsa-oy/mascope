from fastapi import APIRouter, Query, BackgroundTasks
from ..controllers.target_collections_controller import (
    get_target_collections,
    get_target_collection,
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
    target_collection_type: str = Query(
        None, description="Filter by the type of the target collection."
    ),
    target_collection_name: str = Query(
        None, description="Filter by the name of the target collection."
    ),
    sort: str = Query(
        None,
        description="The column name by which you want to sort the results. The column name should be one of the columns in the target_collection table.",
    ),
    order: str = Query(
        None,
        description="Can either be asc for ascending order or desc for descending order.",
    ),
    page: int = Query(0, description="The page number for pagination, default 0"),
    limit: int = Query(100, description="The number of results per page."),
):
    return await get_target_collections(
        target_collection_type, target_collection_name, sort, order, page, limit
    )


@target_collections_router.get("/api/target_collections/{target_collection_id}")
async def get_target_collection_route(target_collection_id: str):
    return await get_target_collection(target_collection_id)


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


@target_collections_router.patch("/api/target_collections/{target_collection_id}")
async def update_target_collection_route(
    target_collection_id: str,
    target_collection_update: TargetCollectionUpdate,
    background_tasks: BackgroundTasks,
):
    result = await update_target_collection(
        target_collection_id, target_collection_update, background_tasks
    )

    return {
        "updated_target_collection": result["updated_target_collection"],
        "added_compounds": result["added_compounds"],
        "removed_compounds": result["removed_compounds"],
        "message_logs": result["message_logs"],
    }


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
