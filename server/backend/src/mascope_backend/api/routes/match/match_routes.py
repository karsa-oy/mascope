from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.params import Query

from mascope_backend.api.controllers.match.match_controller import (
    match_compute_batch,
    match_compute_sample,
    match_remove_all,
    match_remove_batch,
    match_remove_sample,
    rematch_batch,
    rematch_batches,
    rematch_sample,
)
from mascope_backend.api.controllers.sample.lib.sample_batches_fetch import (
    fetch_sample_batch,
)
from mascope_backend.api.controllers.samples.lib.samples_fetch import fetch_sample
from mascope_backend.api.lib.api_features import api_route
from mascope_backend.api.lib.exceptions.api_exceptions import ApiException
from mascope_backend.api.models.match.match_pydantic_model import RematchBatchesBody
from mascope_backend.api.new.auth.dependencies import admin_user, editor_user
from mascope_backend.db.id import gen_id


match_router = APIRouter(prefix="/api/match", tags=["Match Management"])


@match_router.post("/rematch/batches")
@api_route(status_code=202)
async def rematch_batches_route(
    body: RematchBatchesBody,
    background_tasks: BackgroundTasks,
    full_remove: bool = Query(
        False,
        description="If True, removes all existing matches before recomputing."
        "If False, removes only orphaned matches.",
    ),
    force: bool = Query(
        False,
        description="If True, bypasses status checks and forces rematch regardless of current status.",
    ),
    user=Depends(editor_user),
):
    """Rematch multiple sample batches"""
    # Get data for notifications
    process_id = gen_id(8)

    background_tasks.add_task(
        rematch_batches,
        sample_batch_ids=body.sample_batch_ids,
        full_remove=full_remove,
        force=force,
        independent_transaction=True,
        user_id=user.id,
        process_id=process_id,
    )

    total_batches = len(body.sample_batch_ids)
    return {
        "message": f"Rematching {total_batches} sample batch{'es' if total_batches != 1 else ''}, please wait.",
        "process_id": process_id,
    }


@match_router.post("/rematch/batch/{sample_batch_id}")
@api_route(status_code=202)
async def rematch_batch_route(
    sample_batch_id: str,
    background_tasks: BackgroundTasks,
    full_remove: bool = Query(
        False,
        description="If True, removes all existing matches before recomputing."
        "If False, removes only orphaned matches.",
    ),
    force: bool = Query(
        False,
        description="If True, bypasses status checks and forces rematch regardless of current status.",
    ),
    user=Depends(editor_user),
):
    """
    Rematch a specific sample batch by removing orphaned/all matches and recomputing them
    for all samples in the batch

    - Processing batches cannot be rematched
    - Ready batches require force=true to rematch
    """
    # Verify the existance of sample batch
    sample_batch = await fetch_sample_batch(sample_batch_id)

    # Early status check - processing is never bypassable
    msg = f"Sample batch '{sample_batch.sample_batch_name}' is "
    notification_data = {"sample_batch_id": sample_batch_id}
    match sample_batch.status:
        case "processing":
            msg += (
                "currently processing. Please wait for completion and try again later."
            )
            raise ApiException(msg, notification_data, 409)
        case "ready" if not force:
            msg += "already matched - please use 'rematch' option if you want to recompute matches"
            raise ApiException(msg, notification_data, 409)
        case _:
            # "rematch" status or force=True with "ready" - proceed
            pass

    # Get data for notifications
    process_id = gen_id(8)

    background_tasks.add_task(
        rematch_batch,
        sample_batch_id=sample_batch_id,
        full_remove=full_remove,
        force=force,
        independent_transaction=True,
        user_id=user.id,
        process_id=process_id,
    )
    return {
        "message": f"Rematching sample batch '{sample_batch.sample_batch_name}', please wait.",
        "process_id": process_id,
    }


@match_router.post("/compute/batch/{sample_batch_id}")
@api_route(status_code=202)
async def match_compute_batch_route(
    sample_batch_id: str,
    background_tasks: BackgroundTasks,
    user=Depends(editor_user),
):
    """Compute matches for a specific sample batch."""
    # Verify the existance of sample batch
    sample_batch = await fetch_sample_batch(sample_batch_id)

    # Get data for notifications
    process_id = gen_id(8)

    background_tasks.add_task(
        match_compute_batch,
        sample_batch_id=sample_batch_id,
        independent_transaction=True,
        user_id=user.id,
        process_id=process_id,
    )
    return {
        "message": f"Computing matches for sample batch '{sample_batch.sample_batch_name}', please wait.",
        "process_id": process_id,
    }


@match_router.delete("/remove/batch/{sample_batch_id}")
@api_route(status_code=202)
async def match_remove_batch_route(
    sample_batch_id: str,
    background_tasks: BackgroundTasks,
    full_remove: bool = Query(
        False,
        description="If True, removes all existing matches before recomputing."
        "If False, removes only orphaned matches.",
    ),
    user=Depends(editor_user),
):
    """
    Remove orphaned/all matches for a specific sample batch.

    By default, removes only orphaned matches.
    Use full_remove=true to remove all matches.
    """
    # Verify the existance of sample batch
    sample_batch = await fetch_sample_batch(sample_batch_id)

    # Get data for notifications
    process_id = gen_id(8)

    background_tasks.add_task(
        match_remove_batch,
        sample_batch_id=sample_batch_id,
        full_remove=full_remove,
        independent_transaction=True,
        user_id=user.id,
        process_id=process_id,
    )
    return {
        "message": f"Removing matches for sample batch '{sample_batch.sample_batch_name}', please wait.",
        "process_id": process_id,
    }


@match_router.post("/rematch/sample/{sample_item_id}")
@api_route(status_code=202, token_access=True)
async def rematch_sample_route(
    sample_item_id: str,
    background_tasks: BackgroundTasks,
    full_remove: bool = Query(
        False,
        description="If True, removes all existing matches before recomputing."
        "If False, removes only orphaned matches.",
    ),
    user=Depends(editor_user),
):
    """
    Rematch a specific sample by removing orphaned/all matches and recomputing.

    By default, performs partial rematching by removing only orphaned matches.
    Use full_remove=true for complete reset and rematch.
    """
    # Verify the existence of sample item
    sample = await fetch_sample(sample_item_id)

    # Get data for notifications
    process_id = gen_id(8)

    background_tasks.add_task(
        rematch_sample,
        sample_item_id=sample_item_id,
        full_remove=full_remove,
        independent_transaction=True,
        user_id=user.id,
        process_id=process_id,
    )

    return {
        "message": f"Rematching sample '{sample.sample_item_name}', please wait.",
        "process_id": process_id,
    }


@match_router.delete("/remove/sample/{sample_item_id}")
@api_route(status_code=202)
async def match_remove_sample_route(
    sample_item_id: str,
    background_tasks: BackgroundTasks,
    full_remove: bool = Query(
        False,
        description="If True, removes all existing matches before recomputing."
        "If False, removes only orphaned matches.",
    ),
    user=Depends(editor_user),
):
    """
    Remove orphaned/all matches for a specific sample.

    By default, removes only orphaned matches.
    Use full_remove=true to remove all matches.

    """
    # Verify the existance of sample item
    sample = await fetch_sample(sample_item_id)

    # Get data for notifications
    process_id = gen_id(8)

    background_tasks.add_task(
        match_remove_sample,
        sample_item_id=sample_item_id,
        full_remove=full_remove,
        independent_transaction=True,
        user_id=user.id,
        process_id=process_id,
    )
    return {
        "message": f"Removing matches for sample '{sample.sample_item_name}', please wait.",
        "process_id": process_id,
    }


@match_router.post("/compute/sample/{sample_item_id}")
@api_route(status_code=202)
async def match_compute_sample_route(
    sample_item_id: str,
    background_tasks: BackgroundTasks,
    user=Depends(editor_user),
):
    """Compute matches for a specific sample."""
    # Verify the existance of sample item
    sample = await fetch_sample(sample_item_id)

    # Get data for notifications
    process_id = gen_id(8)
    background_tasks.add_task(
        match_compute_sample,
        sample_item_id=sample_item_id,
        independent_transaction=True,
        user_id=user.id,
        process_id=process_id,
    )
    return {
        "message": f"Computing matches for sample '{sample.sample_item_name}', please wait.",
        "process_id": process_id,
    }


@match_router.delete("/remove/all")
@api_route()
async def match_remove_all_route(user=Depends(admin_user)):
    """
    Endpoint to delete all match data across the system.
    """
    return await match_remove_all()
