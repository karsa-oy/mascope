from fastapi import APIRouter, Query
from ..utils.api_features import api_route
from ..controllers.samples_controller import (
    get_sample,
    get_samples,
    init_batch_match_filter,
    init_sample_match_filter,
    get_sample_ion_matches,
    get_sample_compound_matches,
)
from ..models.pydantic_models.sample_pydantic_model import (
    GetSamplesBody,
    GetSampleBody,
    GetSampleMatchFilterBody,
    GetSampleIonMatchesBody,
    GetSampleCompoundMatchesBody,
)

samples_router = APIRouter()


@samples_router.post("/api/samples")
@api_route()
async def get_samples_route(
    body: GetSamplesBody,
):
    result = await get_samples(**body.dict())

    # Default message
    message = "Samples with no match info"
    # Check if batch match filter was initialized and there are sample matches
    if body.sample_batch_id and body.batch_matches_info:
        matched_samples = any(sample.get("matched", 0) > 0 for sample in result["data"])
        message = (
            "Batch match filter successfully initialized"
            if matched_samples
            else "No matches found for the batch"
        )
    response = {
        "results": result["results"],
        "message": message,
        "data": result["data"],
    }

    # Conditionally add batch_matches_info
    if "batch_matches_info" in result:
        response["batch_matches_info"] = result["batch_matches_info"]

    return response


@samples_router.post("/api/samples/{sample_item_id}")
@api_route()
async def get_sample_route(
    sample_item_id: str,
    body: GetSampleBody,
):
    sample_data = await get_sample(sample_item_id=sample_item_id, **body.dict())

    if sample_data and body.sample_matches_info:
        if sample_data and sample_data.get("matched", 0) > 0:
            message = "Sample and match information retrieved successfully"
        else:
            message = "Sample retrieved successfully, no matches found for the sample"
    else:
        message = "Sample retrieved successfully"

    return {
        "message": message,
        "data": sample_data,
    }


@samples_router.post("/api/samples/{sample_item_id}/ion_matches")
@api_route()
async def get_sample_ion_matches_route(
    sample_item_id: str,
    body: GetSampleIonMatchesBody,
):
    data = await get_sample_ion_matches(
        sample_item_id=sample_item_id,
        target_ion_id=body.target_ion_id,
        target_collection_id=body.target_collection_id,
        filter_params=body.filter_params,
        alarms_list=body.alarms_list,
    )

    match_ions_count = len(data["match_ions"]) > 0
    match_isotopes_count = len(data["match_isotopes"]) > 0
    if match_ions_count or match_isotopes_count:
        message = "Match information retrieved successfully"
    else:
        message = "No matches found for the specified criteria"

    return {
        "message": message,
        "data": data,
    }


@samples_router.post("/api/samples/{sample_item_id}/compound_matches")
@api_route()
async def get_sample_compound_matches_route(
    sample_item_id: str,
    body: GetSampleCompoundMatchesBody,
):
    data = await get_sample_compound_matches(
        sample_item_id=sample_item_id,
        target_compound_formula=body.target_compound.target_compound_formula,
        target_compound_name=body.target_compound.target_compound_name,
        filter_params=body.filter_params,
    )

    match_compounds_count = len(data["match_compounds"]) > 0

    if match_compounds_count:
        compound = data["match_compounds"][0].get("target_compound_formula")
        message = f"Match information for compound '{compound}' retrieved successfully"
    else:
        compound = body.target_compound.target_compound_formula
        message = f"No matches found for the specified compound '{compound}'"

    return {
        "message": message,
        "data": data,
    }


@samples_router.get("/api/samples/batch_match_filter/{sample_batch_id}")
@api_route()
async def batch_match_filter_route(
    sample_batch_id: str,
    include_match_interference: bool = Query(
        True, description="Include match interference data in the response"
    ),
):
    batch_match_filter_data = await init_batch_match_filter(
        sample_batch_id, include_match_interference
    )
    message = (
        "Batch match filter successfully initialized"
        if len(batch_match_filter_data) > 0
        else "No matches found for the batch"
    )
    return {
        "results": len(batch_match_filter_data),
        "message": message,
        "data": batch_match_filter_data,
    }


@samples_router.post("/api/samples/{sample_item_id}/sample_match_filter")
@api_route()
async def sample_match_filter_route(
    sample_item_id: str,
    body: GetSampleMatchFilterBody,
):
    data = await init_sample_match_filter(
        sample_item_id=sample_item_id,
        filter_params=body.filter_params,
        target_ion_id=body.target_ion_id,
    )

    if body.target_ion_id and body.filter_params:
        message = (
            "Sample match filter for target ion successfully initialized"
            if len(data) > 0
            else "No matches found for the specified target ion in the sample"
        )
    else:
        message = (
            "Sample match filter successfully initialized"
            if len(data) > 0
            else "No matches found for the sample"
        )

    return {
        "results": len(data),
        "message": message,
        "data": data,
    }
