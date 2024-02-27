from fastapi import APIRouter, BackgroundTasks, Query, Request
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder


from ..controllers.target_collections_controller import (
    get_target_collections,
    get_target_collection,
    create_target_collection,
    delete_target_collection,
    update_target_collection,
)
from ..models.pydantic_models.target_collection_pydantic_model import (
    TargetCollectionCreateBody,
    TargetCollectionUpdateBody,
)
from ..exceptions import ApiException

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
    request: Request,
    body: TargetCollectionCreateBody,
    background_tasks: BackgroundTasks,
):
    try:
        sid = request.headers.get("X-SID")
        result = await create_target_collection(body, background_tasks, sid)
        message_logs = result["message_logs"]
        result_data = jsonable_encoder(result["new_target_collection"])
        return JSONResponse(
            status_code=201,
            content={
                "message": f"Target collection {body.target_collection_name} created successfully.",
                "message_logs": message_logs,
                "data": result_data,
            },
        )
    except ApiException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"error": e.user_message, "detail": e.tech_message},
        )


@target_collections_router.patch("/api/target_collections/{target_collection_id}")
async def update_target_collection_route(
    request: Request,
    target_collection_id: str,
    body: TargetCollectionUpdateBody,
    background_tasks: BackgroundTasks,
):
    try:
        sid = request.headers.get("X-SID")
        result = await update_target_collection(
            target_collection_id, body, background_tasks, sid
        )
        message_logs = result["message_logs"]
        result_data = jsonable_encoder(result["updated_target_collection"])
        return JSONResponse(
            status_code=200,
            content={
                "message": f"Target collection {body.target_collection_name} updated successfully.",
                "message_logs": message_logs,
                "data": result_data,
            },
        )
    except ApiException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"error": e.user_message, "detail": e.tech_message},
        )


@target_collections_router.delete("/api/target_collections/{target_collection_id}")
async def delete_target_collection_route(
    request: Request,
    target_collection_id: str,
    background_tasks: BackgroundTasks,
    delete_orphan_compounds: bool = Query(
        False,
        description="Delete orphan compounds associated with the target collection",
    ),
):
    try:
        sid = request.headers.get("X-SID")
        result = await delete_target_collection(
            target_collection_id, background_tasks, delete_orphan_compounds, sid
        )
        message = result["message"]
        return JSONResponse(
            status_code=200,
            content={
                "message": message,
            },
        )
    except ApiException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"error": e.user_message, "detail": e.tech_message},
        )
