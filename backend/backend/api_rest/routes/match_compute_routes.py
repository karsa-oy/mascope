from fastapi import APIRouter, BackgroundTasks
from typing import List

from ..controllers.match_compute_controller import match_compute_batches
from ..models.pydantic_models.sample_batch_pydantic_model import SampleBatchComputeMatch

match_compute_router = APIRouter()


@match_compute_router.post("/api/match_compute/batches")
async def match_compute_batches_route(
    sample_batches: List[SampleBatchComputeMatch], background_tasks: BackgroundTasks
):
    background_tasks.add_task(match_compute_batches, sample_batches)
    return {"status": "Match computation started for batches"}
