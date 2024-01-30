from fastapi import APIRouter, BackgroundTasks

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
    RematchBody,
    MatchComputeBody,
    MatchRemovePayload,
)

match_router = APIRouter()


@match_router.post("/api/match/batches/rematch")
async def match_batches_compute_route(
    body: RematchBatchesBody,
    background_tasks: BackgroundTasks,
):
    background_tasks.add_task(
        rematch_batches,
        body.sample_batches,
        body.added_target_compound_ids,
        body.added_ionization_mechanism_ids,
        body.removed_target_compound_ids,
        body.removed_ionization_mechanism_ids,
    )
    return {"status": "Rematching process started for sample batches"}


@match_router.post("/api/match/batch/{sample_batch_id}/rematch")
async def rematch_sample_route(
    sample_batch_id: str,
    body: RematchBody,
    background_tasks: BackgroundTasks,
):
    background_tasks.add_task(
        rematch_batch,
        sample_batch_id,
        body.added_target_compound_ids,
        body.added_ionization_mechanism_ids,
        body.removed_target_compound_ids,
        body.removed_ionization_mechanism_ids,
        body.independent_transaction,
    )
    return {"status": f"Rematching process started for sample batch {sample_batch_id}"}


@match_router.post("/api/match/batch/{sample_batch_id}/compute")
async def add_sample_matches_route(
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
async def add_sample_matches_route(
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
