from fastapi import APIRouter, BackgroundTasks
from typing import List

from ..controllers.match_controller import (
    match_batches_compute,
    match_item_compute,
    match_item_remove,
)
from ..models.pydantic_models.match_pydantic_model import (
    MatchComputeBatch,
    MatchComputeItem,
)

match_router = APIRouter()


@match_router.post("/api/match/batches/compute")
async def match_batches_compute_route(
    sample_batches: List[MatchComputeBatch], background_tasks: BackgroundTasks
):
    background_tasks.add_task(match_batches_compute, sample_batches)
    return {"status": "Match computation started for sample batches"}


@match_router.post("/api/match/item/compute")
async def match_sample_compute_route(
    sample: MatchComputeItem, background_tasks: BackgroundTasks
):
    background_tasks.add_task(match_item_compute, sample)
    return {"status": "Match computation started for sample item"}


# @match_router.delete("/api/match/item/remove")
# async def match_sample_remove_route(
#     sample: MatchComputeBatch, background_tasks: BackgroundTasks
# ):
#     background_tasks.add_task(match_item_remove, sample)
#     return {"status": "Removal of matches for sample item"}
