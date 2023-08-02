from fastapi import APIRouter
from ..controllers.target_collections_controller import (
    get_target_collection_by_id,
    get_target_collections,
    create_target_collection,
    delete_target_collection,
)
from ..models.pydantic_models.target_collection_pydantic_model import (
    TargetCollectionCreate,
)


target_collections_router = APIRouter()


@target_collections_router.get("/api/target_collections")
async def get_target_collections_route(
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 10,
):
    return await get_target_collections(sort, order, page, limit)


@target_collections_router.get("/api/target_collections/{target_collection_id}")
async def get_target_collection_by_id_route(target_collection_id: str):
    return await get_target_collection_by_id(target_collection_id)


@target_collections_router.post("/api/target_collections")
async def create_target_collection_route(target_collection: TargetCollectionCreate):
    result = await create_target_collection(target_collection)
    response = {
        "new_target_collection": result["new_target_collection"],
        "created_compounds_count": result["created_compounds_count"],
        "created_compounds": result["created_compounds"],
        "existing_compounds_count": result["existing_compounds_count"],
        "existing_compounds": result["existing_compounds"],
    }
    return response


@target_collections_router.delete("/api/target_collections/{target_collection_id}")
async def delete_target_collection_route(target_collection_id: str):
    return await delete_target_collection(target_collection_id)
