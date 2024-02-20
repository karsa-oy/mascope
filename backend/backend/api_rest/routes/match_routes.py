from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from ..exceptions import ApiException

from ..controllers.match_controller import (
    rematch_batches,
    rematch_batch,
    match_batch_compute,
    match_batch_remove,
    rematch_sample,
    match_sample_compute,
    match_sample_remove,
)
from ..models.pydantic_models.match_pydantic_model import (
    RematchBatchesBody,
    RematchBatchBody,
    ProgressProperties,
    RematchBody,
    MatchComputeBody,
    MatchRemovePayload,
)

match_router = APIRouter()


@match_router.post("/api/match/batches/rematch")
async def rematch_batches_route(
    request: Request,
    body: RematchBatchesBody,
    background_tasks: BackgroundTasks,
):
    try:
        sid = request.headers.get("X-SID")
        background_tasks.add_task(rematch_batches, body, sid)
        return JSONResponse(
            status_code=200,
            content={
                "message": f"Rematching process started for sample batches",
            },
        )
    except ApiException as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"error": e.user_message, "detail": e.tech_message},
        )


@match_router.post("/api/match/batch/{sample_batch_id}/rematch")
async def rematch_batch_route(
    sample_batch_id: str,
    body: RematchBatchBody,
    background_tasks: BackgroundTasks,
):
    # prepare data for rematching
    rematch_body = RematchBatchBody(
        sample_batch_id=sample_batch_id,
        workspace_id=body.workspace_id,
        added_target_compound_ids=body.added_target_compound_ids,
        added_ionization_mechanism_ids=body.added_ionization_mechanism_ids,
        removed_target_compound_ids=body.removed_target_compound_ids,
        removed_ionization_mechanism_ids=body.removed_ionization_mechanism_ids,
        independent_transaction=body.independent_transaction,
        progress_properties=ProgressProperties(
            progress_type="rematch_batch",
        ),
    )

    background_tasks.add_task(
        rematch_batch,
        rematch_body.sample_batch_id,
        rematch_body.workspace_id,
        rematch_body.added_target_compound_ids,
        rematch_body.added_ionization_mechanism_ids,
        rematch_body.removed_target_compound_ids,
        rematch_body.removed_ionization_mechanism_ids,
        rematch_body.independent_transaction,
        rematch_body.progress_properties,
    )
    return {"status": f"Rematching process started for sample batch {sample_batch_id}"}


@match_router.post("/api/match/batch/{sample_batch_id}/compute")
async def match_batch_compute_route(
    sample_batch_id: str,
    body: MatchComputeBody,
    background_tasks: BackgroundTasks,
):
    background_tasks.add_task(
        match_batch_compute,
        sample_batch_id,
        body.added_target_compound_ids,
        body.added_ionization_mechanism_ids,
        body.independent_transaction,
    )
    return {"status": f"Match computation started for batch {sample_batch_id}"}


@match_router.delete("/api/match/batch/{sample_batch_id}/remove")
async def match_batch_remove_route(
    sample_batch_id: str,
    payload: MatchRemovePayload,
):
    # Unpack the payload
    removed_target_compound_ids = payload.removed_target_compound_ids
    removed_ionization_mechanism_ids = payload.removed_ionization_mechanism_ids
    independent_transaction = payload.independent_transaction

    return await match_batch_remove(
        sample_batch_id,
        removed_target_compound_ids,
        removed_ionization_mechanism_ids,
        independent_transaction,
    )


@match_router.post("/api/match/sample/{sample_item_id}/rematch")
async def rematch_sample_route(
    sample_item_id: str,
    body: RematchBody,
    background_tasks: BackgroundTasks,
):
    background_tasks.add_task(
        rematch_sample,
        sample_item_id,
        body.added_target_compound_ids,
        body.added_ionization_mechanism_ids,
        body.removed_target_compound_ids,
        body.removed_ionization_mechanism_ids,
        body.independent_transaction,
    )
    return {"status": f"Rematching process started for sample item {sample_item_id}"}


@match_router.delete("/api/match/sample/{sample_item_id}/remove")
async def match_sample_remove_route(
    sample_item_id: str,
    payload: MatchRemovePayload,
):
    # Unpack the payload
    removed_target_compound_ids = payload.removed_target_compound_ids
    removed_ionization_mechanism_ids = payload.removed_ionization_mechanism_ids
    independent_transaction = payload.independent_transaction

    return await match_sample_remove(
        sample_item_id,
        removed_target_compound_ids,
        removed_ionization_mechanism_ids,
        independent_transaction,
    )


@match_router.post("/api/match/sample/{sample_item_id}/compute")
async def match_sample_compute_route(
    sample_item_id: str,
    body: MatchComputeBody,
    background_tasks: BackgroundTasks,
):
    background_tasks.add_task(
        match_sample_compute,
        sample_item_id,
        body.added_target_compound_ids,
        body.added_ionization_mechanism_ids,
        body.independent_transaction,
    )
    return {"status": "Match computation started for sample {sample_item_id}"}
