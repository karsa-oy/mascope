from fastapi import APIRouter
from mascope_server.api.lib.api_features import api_route
from mascope_server.api.lib.exceptions.api_exceptions import ApiException
from mascope_server.api.controllers.match.aggregate.match_aggregate_controller import (
    aggregate_match_isotope_filtered_data,
    aggregate_matches,
    aggregate_and_create_matches,
)
from mascope_server.api.controllers.match.aggregate.sample.match_aggregate_sample_controller import (
    aggregate_sample_match_ion,
    aggregate_sample_match_compound,
    get_sample_and_aggregated_matches,
)
from mascope_server.api.controllers.sample.items.sample_items_controller import (
    get_sample_item,
)
from mascope_server.api.models.match.aggregate.match_aggregate_pydantic_model import (
    AggregateMatchIsotopeFilteredDataBody,
    AggregateSampleMatchIonBody,
    AggregateSampleMatchCompoundBody,
    AggregateAndCreateMatchesBody,
)


match_aggregate_sample_router = APIRouter()


@match_aggregate_sample_router.post(
    "/api/match/aggregate/sample/{sample_item_id}/isotope"
)
@api_route()
async def aggregate_sample_match_isotope_filtered_data_route(
    sample_item_id: str,
    body: AggregateMatchIsotopeFilteredDataBody,
):
    # Verify the existance of sample item
    sample = await get_sample_item(sample_item_id)
    sample_item_name = sample["sample_item_name"]

    data = await aggregate_match_isotope_filtered_data(
        sample_item_id=sample_item_id,
        target_ion_id=body.target_ion_id,
        filter_params=body.filter_params,
        include_match_interference=body.include_match_interference,
    )
    if not data.empty:
        data_dict = data.to_dict("records")
        return {
            "results": len(data_dict),
            "message": (
                f"Filtered match isotope data fetched successfully for sample '{sample_item_name}'"
            ),
            "data": data_dict,
        }
    return {
        "message": f"No match isotope data found for sample '{sample_item_name}'",
        "results": 0,
        "data": [],
    }


@match_aggregate_sample_router.post("/api/match/aggregate/sample/{sample_item_id}/ion")
@api_route()
async def aggregate_sample_match_ion_route(
    sample_item_id: str,
    body: AggregateSampleMatchIonBody,
):
    return await aggregate_sample_match_ion(
        sample_item_id=sample_item_id,
        target_ion_id=body.target_ion_id,
        target_collection_id=body.target_collection_id,
        filter_params=body.filter_params,
    )


@match_aggregate_sample_router.post(
    "/api/match/aggregate/sample/{sample_item_id}/compound"
)
@api_route()
async def aggregate_sample_match_compound_route(
    sample_item_id: str,
    body: AggregateSampleMatchCompoundBody,
):
    return await aggregate_sample_match_compound(
        sample_item_id=sample_item_id,
        target_compound_formula=body.target_compound.target_compound_formula,
        target_compound_name=body.target_compound.target_compound_name,
        filter_params=body.filter_params,
    )


@match_aggregate_sample_router.post("/api/match/aggregate/sample/{sample_item_id}")
@api_route()
async def aggregate_sample_matches_route(
    sample_item_id: str,
    body: AggregateMatchIsotopeFilteredDataBody,
):
    # Verify the existance of sample item
    sample = await get_sample_item(sample_item_id)
    sample_item_name = sample["sample_item_name"]

    result = await aggregate_matches(
        sample_item_id=sample_item_id,
        target_ion_id=body.target_ion_id,
        filter_params=body.filter_params,
    )
    if result.get("results", 0) == 0:
        message = f"No match data found for sample '{sample_item_name}'"
    else:
        message = f"Match data aggregated successfully for sample '{sample_item_name}'"

    return {
        "message": message,
        "results": result.get("results", 0),
        "data": result.get("data", []),
    }


@match_aggregate_sample_router.post("/api/match/aggregate/sample/{sample_item_id}/save")
@api_route(
    status_code=201,
)
async def aggregate_and_create_sample_matches_route(
    sample_item_id: str,
    body: AggregateAndCreateMatchesBody,
):
    result = await aggregate_and_create_matches(
        sample_item_id=sample_item_id,
        target_ion_id=body.target_ion_id,
        filter_params=body.filter_params,
    )

    errors = result.get("errors", [])
    message = result.get("message", "")
    if errors:
        raise ApiException(
            message,
            {
                "errors": errors,
            },
            409,
        )

    return {
        "message": message,
        "message_logs": result.get("message_logs", []),
    }


@match_aggregate_sample_router.get("/api/match/aggregate/sample/{sample_item_id}/all")
@api_route()
async def get_sample_aggregate_matches_route(
    sample_item_id: str,
):
    sample_data = await get_sample_and_aggregated_matches(sample_item_id=sample_item_id)
    if sample_data and sample_data.get("matched", 0) > 0:
        message = "Sample and match information retrieved successfully"
    else:
        message = "Sample retrieved successfully, no matches found for the sample"

    return {
        "message": message,
        "data": sample_data,
    }
