from fastapi import APIRouter
from typing import List

from ..controllers.sample_batches_controller import (
    get_sample_batch_by_id,
    get_sample_batches,
    create_sample_batch,
    delete_sample_batch,
    update_sample_batch,
    reload_sample_batch,
    compute_sample_batch_matches,
)
from ..models.pydantic_models.sample_batch_pydantic_model import (
    SampleBatchCreate,
    SampleBatchUpdate,
    SampleBatchComputeMatch,
)

sample_batches_router = APIRouter()


@sample_batches_router.get("/api/sample_batches")
async def get_sample_batches_route(
    workspace_id: str = None,
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 100,
):
    return await get_sample_batches(workspace_id, sort, order, page, limit)


@sample_batches_router.get("/api/sample_batches/{sample_batch_id}")
async def get_sample_batch_by_id_route(sample_batch_id: str):
    return await get_sample_batch_by_id(sample_batch_id)


@sample_batches_router.post("/api/sample_batches")
async def create_sample_batch_route(sample_batch: SampleBatchCreate):
    return await create_sample_batch(sample_batch)


@sample_batches_router.delete("/api/sample_batches/{sample_batch_id}")
async def delete_sample_batch_route(sample_batch_id: str):
    return await delete_sample_batch(sample_batch_id)


@sample_batches_router.patch("/api/sample_batches/{sample_batch_id}")
async def update_sample_batch_route(
    sample_batch_id: str, sample_batch: SampleBatchUpdate
):
    return await update_sample_batch(sample_batch_id, sample_batch)


@sample_batches_router.post("/api/sample_batches/{sample_batch_id}/reload")
async def reload_sample_batch_route(sample_batch_id: str):
    return await reload_sample_batch(sample_batch_id)


@sample_batches_router.post("/api/sample_batches/compute_matches")
async def compute_sample_batch_matches_route(
    sample_batches: List[SampleBatchComputeMatch],
):
    return await compute_sample_batch_matches(sample_batches)
