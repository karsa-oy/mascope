from fastapi import APIRouter, BackgroundTasks, Query, Request, Depends
from backend.db.id import gen_id
from ..utils.api_features import api_route
from ..controllers.target_collections_controller import (
    get_target_collections,
    get_target_collection,
    create_target_collection,
    delete_target_collection,
    update_target_collection,
)
from ..models.pydantic_models.target_collection_pydantic_model import (
    GetTargetCollectionsQueryParams,
    TargetCollectionCreateBody,
    TargetCollectionUpdateBody,
)

target_collections_router = APIRouter()


@target_collections_router.get("/api/target_collections")
@api_route()
async def get_target_collections_route(
    query_params: GetTargetCollectionsQueryParams = Depends(),
):
    return await get_target_collections(**query_params.dict())


@target_collections_router.get("/api/target_collections/{target_collection_id}")
@api_route()
async def get_target_collection_route(target_collection_id: str):
    return await get_target_collection(target_collection_id)


@target_collections_router.post("/api/target_collections")
@api_route(
    status_code=201,
)
async def create_target_collection_route(
    request: Request,
    body: TargetCollectionCreateBody,
    background_tasks: BackgroundTasks,
):
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


@target_collections_router.patch("/api/target_collections/{target_collection_id}")
@api_route()
async def update_target_collection_route(
    request: Request,
    target_collection_id: str,
    body: TargetCollectionUpdateBody,
    background_tasks: BackgroundTasks,
):
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


@target_collections_router.delete("/api/target_collections/{target_collection_id}")
@api_route()
async def delete_target_collection_route(
    request: Request,
    target_collection_id: str,
    background_tasks: BackgroundTasks,
    delete_orphan_compounds: bool = Query(
        False,
        description="Delete orphan compounds associated with the target collection",
    ),
):
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
