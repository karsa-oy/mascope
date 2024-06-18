from fastapi import APIRouter, BackgroundTasks, Request
from mascope_server.db.id import gen_id
from ..utils.api_features import api_route

from ..controllers.match_controller import (
    rematch_batches,
    rematch_batch,
    match_batch_compute,
    match_batch_remove,
    rematch_sample,
    match_sample_compute,
    match_sample_remove,
)
from ..controllers.sample_batches_controller import get_sample_batch
from ..controllers.sample_items_controller import get_sample
from ..models.pydantic_models.match_pydantic_model import (
    RematchBatchesBody,
    RematchBatchBody,
    RematchBody,
    MatchComputeBody,
    MatchRemovePayload,
)

match_router = APIRouter()


@match_router.post("/api/match/batches/rematch")
@api_route(
    status_code=202,
)
async def rematch_batches_route(
    request: Request,
    body: RematchBatchesBody,
    background_tasks: BackgroundTasks,
):
    # Get data for notifications
    sid = request.headers.get("X-SID")
    process_id = gen_id(8)

    background_tasks.add_task(
        rematch_batches,
        rematch_batches_body=body,
        independent_transaction=True,
        sid=sid,
        process_id=process_id,
    )

    total_batches = len(body.sample_batches)
    return {
        "message": f"Rematching {total_batches} sample batch{'es' if total_batches != 1 else ''}, please wait.",
        "process_id": process_id,
    }


@match_router.post("/api/match/batch/{sample_batch_id}/rematch")
@api_route(
    status_code=202,
)
async def rematch_batch_route(
    request: Request,
    sample_batch_id: str,
    body: RematchBatchBody,
    background_tasks: BackgroundTasks,
):
    # Verify the existance of sample batch
    sample_batch = await get_sample_batch(sample_batch_id)
    sample_batch_name = sample_batch["sample_batch_name"]

    # Get data for notifications
    sid = request.headers.get("X-SID")
    process_id = gen_id(8)

    background_tasks.add_task(
        rematch_batch,
        sample_batch_id=sample_batch_id,
        added_target_compound_ids=body.added_target_compound_ids,
        added_ionization_mechanism_ids=body.added_ionization_mechanism_ids,
        removed_target_compound_ids=body.removed_target_compound_ids,
        independent_transaction=True,
        sid=sid,
        process_id=process_id,
    )
    return {
        "message": f"Rematching sample batch '{sample_batch_name}', please wait.",
        "process_id": process_id,
    }


@match_router.post("/api/match/batch/{sample_batch_id}/compute")
@api_route(
    status_code=202,
)
async def match_batch_compute_route(
    request: Request,
    sample_batch_id: str,
    body: MatchComputeBody,
    background_tasks: BackgroundTasks,
):
    # Verify the existance of sample batch
    sample_batch = await get_sample_batch(sample_batch_id)
    sample_batch_name = sample_batch["sample_batch_name"]

    # Get data for notifications
    sid = request.headers.get("X-SID")
    process_id = gen_id(8)

    background_tasks.add_task(
        match_batch_compute,
        sample_batch_id=sample_batch_id,
        added_target_compound_ids=body.added_target_compound_ids,
        added_ionization_mechanism_ids=body.added_ionization_mechanism_ids,
        independent_transaction=True,
        sid=sid,
        process_id=process_id,
    )
    return {
        "message": f"Computing matches for sample batch '{sample_batch_name}', please wait.",
        "process_id": process_id,
    }


@match_router.delete("/api/match/batch/{sample_batch_id}/remove")
@api_route(
    status_code=202,
)
async def match_batch_remove_route(
    request: Request,
    sample_batch_id: str,
    payload: MatchRemovePayload,
    background_tasks: BackgroundTasks,
):
    # Verify the existance of sample batch
    sample_batch = await get_sample_batch(sample_batch_id)
    sample_batch_name = sample_batch["sample_batch_name"]

    # Get data for notifications
    sid = request.headers.get("X-SID")
    process_id = gen_id(8)

    background_tasks.add_task(
        match_batch_remove,
        sample_batch_id=sample_batch_id,
        removed_target_compound_ids=payload.removed_target_compound_ids,
        removed_ionization_mechanism_ids=payload.removed_ionization_mechanism_ids,
        independent_transaction=True,
        sid=sid,
        process_id=process_id,
    )
    return {
        "message": f"Removing matches for sample batch '{sample_batch_name}', please wait.",
        "process_id": process_id,
    }


@match_router.post("/api/match/sample/{sample_item_id}/rematch")
@api_route(
    status_code=202,
)
async def rematch_sample_route(
    request: Request,
    sample_item_id: str,
    body: RematchBody,
    background_tasks: BackgroundTasks,
):
    # Verify the existance of sample item
    sample = await get_sample(sample_item_id)
    sample_item_name = sample["sample_item_name"]

    # Get data for notifications
    sid = request.headers.get("X-SID")
    process_id = gen_id(8)

    background_tasks.add_task(
        rematch_sample,
        sample_item_id=sample_item_id,
        added_target_compound_ids=body.added_target_compound_ids,
        added_ionization_mechanism_ids=body.added_ionization_mechanism_ids,
        removed_target_compound_ids=body.removed_target_compound_ids,
        removed_ionization_mechanism_ids=body.removed_ionization_mechanism_ids,
        independent_transaction=True,
        sid=sid,
        process_id=process_id,
    )
    return {
        "message": f"Rematching sample '{sample_item_name}', please wait.",
        "process_id": process_id,
    }


@match_router.delete("/api/match/sample/{sample_item_id}/remove")
@api_route(
    status_code=202,
)
async def match_sample_remove_route(
    request: Request,
    sample_item_id: str,
    payload: MatchRemovePayload,
    background_tasks: BackgroundTasks,
):
    # Verify the existance of sample item
    sample = await get_sample(sample_item_id)
    sample_item_name = sample["sample_item_name"]

    # Get data for notifications
    sid = request.headers.get("X-SID")
    process_id = gen_id(8)

    background_tasks.add_task(
        match_sample_remove,
        sample_item_id=sample_item_id,
        removed_target_compound_ids=payload.removed_target_compound_ids,
        removed_ionization_mechanism_ids=payload.removed_ionization_mechanism_ids,
        independent_transaction=True,
        sid=sid,
        process_id=process_id,
    )
    return {
        "message": f"Removing matches for sample '{sample_item_name}', please wait.",
        "process_id": process_id,
    }


@match_router.post("/api/match/sample/{sample_item_id}/compute")
@api_route(
    status_code=202,
)
async def match_sample_compute_route(
    request: Request,
    sample_item_id: str,
    body: MatchComputeBody,
    background_tasks: BackgroundTasks,
):
    # Verify the existance of sample item
    sample = await get_sample(sample_item_id)
    sample_item_name = sample["sample_item_name"]

    # Get data for notifications
    sid = request.headers.get("X-SID")
    process_id = gen_id(8)
    background_tasks.add_task(
        match_sample_compute,
        sample_item_id=sample_item_id,
        added_target_compound_ids=body.added_target_compound_ids,
        added_ionization_mechanism_ids=body.added_ionization_mechanism_ids,
        independent_transaction=True,
        sid=sid,
        process_id=process_id,
    )
    return {
        "message": f"Computing matches for sample '{sample_item_name}', please wait.",
        "process_id": process_id,
    }
