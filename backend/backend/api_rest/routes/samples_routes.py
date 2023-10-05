from fastapi import APIRouter
from ..controllers.samples_controller import (
    get_sample_by_id,
    get_samples,
    init_batch_match_filter,
    init_sample_match_filter,
    get_targets,
)
from ..models.pydantic_models.sample_pydantic_model import (
    MatchFilterBody,
    GetSamplesBody,
    FilterParams,
    GetTargetsBody,
)

samples_router = APIRouter()


@samples_router.post("/api/samples")
async def get_samples_route(
    body: GetSamplesBody,
):
    result = await get_samples(
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

    response = {
        "message": result["message"],
        "results": result["results"],
        "data": result["data"],
    }

    if "batch_matches_info" in result and result["batch_matches_info"]:
        response["batch_matches_info"] = result["batch_matches_info"]

    return response


@samples_router.post("/api/samples/init_batch_match_filter")
async def init_match_filter_route(body: MatchFilterBody):
    result = await init_batch_match_filter(body.sample_batch_id, body.filter_params)

    return {
        "results": len(result["data"]),
        "message": result["message"],
        "data": result["data"],
    }


@samples_router.post("/api/samples/init_sample_match_filter")
async def init_match_filter_route(body: MatchFilterBody):
    result = await init_sample_match_filter(
        body.sample_batch_id, body.sample_item_id, body.filter_params
    )

    return {
        "results": len(result["data"]),
        "message": result["message"],
        "data": result["data"],
    }


@samples_router.post("/api/samples/{sample_item_id}")
async def get_sample_by_id_route(sample_item_id: str, filter_params: FilterParams):
    result = await get_sample_by_id(sample_item_id, filter_params)
    return {
        "message": result["message"],
        "data": result["data"],
    }


@samples_router.post("/api/samples_batch_targets")
async def get_targets_route(body: GetTargetsBody):
    result = await get_targets(body.sample_batch_id, body.ion_mechanisms)
    return {"message": "Fetched targets successfully.", "data": result}
