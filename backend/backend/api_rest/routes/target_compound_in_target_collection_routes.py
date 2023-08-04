from typing import List
from fastapi import APIRouter
from ..controllers.target_compound_in_target_collection_controller import (
    get_target_compound_in_target_collection,
    create_target_compound_in_target_collection,
    delete_target_compound_in_target_collection,
)
from ..models.pydantic_models.target_compound_in_target_collection_pydantic_model import (
    TargetCompoundInTargetCollectionBase,
)

target_compound_in_target_collection_router = APIRouter()


@target_compound_in_target_collection_router.get(
    "/api/target_compound_in_target_collections"
)
async def get_target_compound_in_target_collections_route(
    target_compound_id: str = None,
    target_collection_id: str = None,
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 100,
):
    return await get_target_compound_in_target_collection(
        target_compound_id, target_collection_id, sort, order, page, limit
    )


@target_compound_in_target_collection_router.post(
    "/api/target_compound_in_target_collections"
)
async def create_target_compound_in_target_collection_route(
    target_compounds_in_target_collection: List[TargetCompoundInTargetCollectionBase],
):
    result = await create_target_compound_in_target_collection(
        target_compounds_in_target_collection
    )
    response = {
        "added_compounds_to_target_collection_count": len(
            result["added_compounds_to_target_collection"]
        ),
        "added_compounds_to_target_collection": result[
            "added_compounds_to_target_collection"
        ],
        "message-logs": result["message_logs"],
    }
    return response


@target_compound_in_target_collection_router.delete(
    "/api/target_compound_in_target_collections/{target_compound_id}/{target_collection_id}"
)
async def delete_target_compound_in_target_collection_route(
    target_compound_id: str, target_collection_id: str
):
    return await delete_target_compound_in_target_collection(
        target_compound_id, target_collection_id
    )
