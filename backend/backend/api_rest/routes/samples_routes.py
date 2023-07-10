from fastapi import APIRouter
from ..controllers.samples_controller import (
    get_sample_by_id,
    get_samples,
    init_match_filter,
)
from ..models.pydantic_models.sample_pydantic_model import (
    MatchFilterBody,
    GetSamplesBody,
)

samples_router = APIRouter()


@samples_router.post("/api/samples")
async def get_samples_route(
    body: GetSamplesBody,
):
    return await get_samples(
        sample_item_id=body.sample_item_id,
        sample_item_id_active=body.sample_item_id_active,
        sample_file_id=body.sample_file_id,
        sample_batch_id=body.sample_batch_id,
        filename=body.filename,
        instrument=body.instrument,
        sample_item_type=body.sample_item_type,
        minDatetime=body.minDatetime,
        maxDatetime=body.maxDatetime,
        sort=body.sort,
        order=body.order,
        filter_params=body.filter_params,
        page=body.page,
        limit=body.limit,
    )


@samples_router.get("/api/samples/{sample_id}")
async def get_sample_by_id_route(sample_id: str):
    return await get_sample_by_id(sample_id)


@samples_router.post("/api/samples/init_match_filter")
async def init_match_filter_route(body: MatchFilterBody):
    result = await init_match_filter(body.batch_id, body.filter_params)
    return {
        "results": len(result),
        "data": result,
    }
