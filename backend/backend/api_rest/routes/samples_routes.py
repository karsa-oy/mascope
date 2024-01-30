from fastapi import APIRouter, Query, Body
from ..controllers.samples_controller import (
    get_sample,
    get_samples,
    init_batch_match_filter,
    init_sample_match_filter,
    get_sample_ion_matches,
)
from ..models.pydantic_models.sample_pydantic_model import (
    GetSamplesBody,
    GetSampleBody,
    MatchFilterBody,
    GetSampleIonMatchesBody,
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
        page=body.page,
        limit=body.limit,
        batch_matches_info=body.batch_matches_info,
        match_samples=body.match_samples,
        match_compounds=body.match_compounds,
        match_ions=body.match_ions,
        match_isotopes=body.match_isotopes,
        alarms_list=body.alarms_list,
    )
    response = {
        "results": result["results"],
        "message": result["message"],
        "data": result["data"],
    }

    if "batch_matches_info" in result and result["batch_matches_info"]:
        response["batch_matches_info"] = result["batch_matches_info"]

    return response


@samples_router.post("/api/samples/{sample_item_id}")
async def get_sample_route(
    sample_item_id: str,
    body: GetSampleBody,
):
    result = await get_sample(
        sample_item_id, body.alarms_list, body.sample_matches_info
    )
    return {
        "message": result["message"],
        "data": result["data"],
    }


@samples_router.post("/api/samples/{sample_item_id}/ion_matches")
async def get_sample_ion_matches_route(
    sample_item_id: str,
    body: GetSampleIonMatchesBody,
):
    result = await get_sample_ion_matches(
        sample_item_id,
        body.target_ion_id,
        body.target_collection_id,
        body.filter_params,
        body.alarms_list,
    )
    return {
        "message": result["message"],
        "data": result["data"],
    }


@samples_router.get("/api/samples/batch_match_filter/{sample_batch_id}")
async def batch_match_filter_route(
    sample_batch_id: str,
):
    result = await init_batch_match_filter(sample_batch_id)

    return {
        "results": len(result["data"]),
        "message": result["message"],
        "data": result["data"],
    }


@samples_router.post("/api/samples/{sample_item_id}/sample_match_filter")
async def sample_match_filter_route(
    sample_item_id: str,
    body: MatchFilterBody = Body(..., embed=False),
):
    result = await init_sample_match_filter(
        sample_item_id,
        body.filter_params,
        body.target_ion_id,
    )

    return {
        "results": len(result["data"]),
        "message": result["message"],
        "data": result["data"],
    }
