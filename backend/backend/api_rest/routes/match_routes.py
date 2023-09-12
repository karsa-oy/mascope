from fastapi import APIRouter, BackgroundTasks
from typing import List

from ..controllers.match_controller import (
    match_batches_compute,
)
from ..models.pydantic_models.sample_batch_pydantic_model import SampleBatchComputeMatch

match_router = APIRouter()


@match_router.post("/api/match/batches/compute")
async def match_batches_compute_route(
    sample_batches: List[SampleBatchComputeMatch], background_tasks: BackgroundTasks
):
    background_tasks.add_task(match_batches_compute, sample_batches)
    return {"status": "Match computation started for batches"}
