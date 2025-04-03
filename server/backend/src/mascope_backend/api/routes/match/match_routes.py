from fastapi import APIRouter, BackgroundTasks, Depends, Request
from mascope_backend.db.id import gen_id
from mascope_backend.api.new.auth.dependencies import editor_user, admin_user
from mascope_backend.api.lib.api_features import api_route

from mascope_backend.api.controllers.match.match_controller import (
    rematch_batches,
    rematch_batch,
    match_compute_batch,
    match_remove_batch,
    rematch_sample,
    match_compute_sample,
    match_remove_sample,
    match_remove_all,
)
from mascope_backend.api.controllers.sample.batches.sample_batches_controller import (
    get_sample_batch,
)
from mascope_backend.api.controllers.sample.items.sample_items_controller import (
    get_sample_item,
)
from mascope_backend.api.models.match.match_pydantic_model import (
    RematchBatchesBody,
    RematchBatchBody,
    RematchBody,
    MatchComputeBody,
    MatchRemovePayload,
)

match_router = APIRouter(prefix="/api/match", tags=["Match Management"])


@match_router.post("/rematch/batches")
@api_route(status_code=202)
async def rematch_batches_route(
    request: Request,
    body: RematchBatchesBody,
    background_tasks: BackgroundTasks,
    user=Depends(editor_user),
):
    """Rematch multiple sample batches"""
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


@match_router.post("/rematch/batch/{sample_batch_id}")
@api_route(status_code=202)
async def rematch_batch_route(
    request: Request,
    sample_batch_id: str,
    body: RematchBatchBody,
    background_tasks: BackgroundTasks,
    user=Depends(editor_user),
):
    """Rematch a single sample batch."""
    # Verify the existance of sample batch
    sample_batch_result = await get_sample_batch(sample_batch_id)
    sample_batch = sample_batch_result.get("data")
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


@match_router.post("/compute/batch/{sample_batch_id}")
@api_route(status_code=202)
async def match_compute_batch_route(
    request: Request,
    sample_batch_id: str,
    body: MatchComputeBody,
    background_tasks: BackgroundTasks,
    user=Depends(editor_user),
):
    """Compute matches for a specific sample batch."""
    # Verify the existance of sample batch
    sample_batch_result = await get_sample_batch(sample_batch_id)
    sample_batch = sample_batch_result.get("data")
    sample_batch_name = sample_batch["sample_batch_name"]

    # Get data for notifications
    sid = request.headers.get("X-SID")
    process_id = gen_id(8)

    background_tasks.add_task(
        match_compute_batch,
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


@match_router.delete("/remove/batch/{sample_batch_id}")
@api_route(status_code=202)
async def match_remove_batch_route(
    request: Request,
    sample_batch_id: str,
    payload: MatchRemovePayload,
    background_tasks: BackgroundTasks,
    user=Depends(editor_user),
):
    """Remove matches from a specific sample batch."""
    # Verify the existance of sample batch
    sample_batch_result = await get_sample_batch(sample_batch_id)
    sample_batch = sample_batch_result.get("data")
    sample_batch_name = sample_batch["sample_batch_name"]

    # Get data for notifications
    sid = request.headers.get("X-SID")
    process_id = gen_id(8)

    background_tasks.add_task(
        match_remove_batch,
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


@match_router.post("/rematch/sample/{sample_item_id}")
@api_route(status_code=202)
async def rematch_sample_route(
    request: Request,
    sample_item_id: str,
    body: RematchBody,
    background_tasks: BackgroundTasks,
    user=Depends(editor_user),
):
    """Rematch a specific sample."""
    # Verify the existance of sample item
    sample_data = await get_sample_item(sample_item_id)
    sample = sample_data.get("data")
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


@match_router.delete("/remove/sample/{sample_item_id}")
@api_route(status_code=202)
async def match_remove_sample_route(
    request: Request,
    sample_item_id: str,
    payload: MatchRemovePayload,
    background_tasks: BackgroundTasks,
    user=Depends(editor_user),
):
    """Remove matches from a specific sample."""
    # Verify the existance of sample item
    sample_data = await get_sample_item(sample_item_id)
    sample = sample_data.get("data")
    sample_item_name = sample["sample_item_name"]

    # Get data for notifications
    sid = request.headers.get("X-SID")
    process_id = gen_id(8)

    background_tasks.add_task(
        match_remove_sample,
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


@match_router.post("/compute/sample/{sample_item_id}")
@api_route(status_code=202)
async def match_compute_sample_route(
    request: Request,
    sample_item_id: str,
    body: MatchComputeBody,
    background_tasks: BackgroundTasks,
    user=Depends(editor_user),
):
    """Compute matches for a specific sample."""
    # Verify the existance of sample item
    sample_data = await get_sample_item(sample_item_id)
    sample = sample_data.get("data")
    sample_item_name = sample["sample_item_name"]

    # Get data for notifications
    sid = request.headers.get("X-SID")
    process_id = gen_id(8)
    background_tasks.add_task(
        match_compute_sample,
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


@match_router.delete("/remove/all")
@api_route()
async def match_remove_all_route(user=Depends(admin_user)):
    """
    Endpoint to delete all match data across the system.
    """
    return await match_remove_all()
