from fastapi import APIRouter
from ..controllers.samples_controller import (
    get_sample_by_id,
    get_samples,
    init_batch_match_filter,
    init_sample_match_filter,
)
from ..models.pydantic_models.sample_pydantic_model import (
    MatchFilterBody,
    GetSamplesBody,
    FilterParams,
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
        batch_matches_info=body.batch_matches_info,
    )


@samples_router.post("/api/samples/init_batch_match_filter")
async def init_match_filter_route(body: MatchFilterBody):
    result = await init_batch_match_filter(body.sample_batch_id, body.filter_params)

    message = (
        "Batch match filter successfully initialized"
        if len(result) > 0
        else "No matches found"
    )
    return {
        "message": message,
        "results": len(result),
        "data": result,
    }


@samples_router.post("/api/samples/init_sample_match_filter")
async def init_match_filter_route(body: MatchFilterBody):
    result = await init_sample_match_filter(
        body.sample_batch_id, body.sample_item_id, body.filter_params
    )

    message = (
        "Sample match filter successfully initialized"
        if len(result) > 0
        else "No matches found"
    )

    return {
        "message": message,
        "results": len(result),
        "data": result,
    }


@samples_router.post("/api/samples/{sample_item_id}")
async def get_sample_by_id_route(sample_item_id: str, filter_params: FilterParams):
    return await get_sample_by_id(sample_item_id, filter_params)
