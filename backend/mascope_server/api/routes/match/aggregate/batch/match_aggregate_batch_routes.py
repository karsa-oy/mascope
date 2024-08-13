from fastapi import APIRouter
from mascope_server.api.lib.api_features import api_route
from mascope_server.api.lib.exceptions.api_exceptions import ApiException
from mascope_server.api.controllers.match.aggregate.match_aggregate_controller import (
    aggregate_matches,
    aggregate_match_isotope_filtered_data,
    aggregate_and_create_matches,
    aggregate_and_recreate_matches,
)
from mascope_server.api.controllers.match.aggregate.batch.match_aggregate_batch_controller import (
    get_batch_and_aggregated_matches,
)
from mascope_server.api.controllers.sample.batches.sample_batches_controller import (
    get_sample_batch,
)
from mascope_server.api.models.match.aggregate.match_aggregate_pydantic_model import (
    AggregateMatchIsotopeFilteredDataBody,
    AggregateAndCreateMatchesBody,
)


match_aggregate_batch_router = APIRouter()


@match_aggregate_batch_router.post(
    "/api/match/aggregate/batch/{sample_batch_id}/isotope"
)
@api_route()
async def aggregate_batch_match_isotope_filtered_data_route(
    sample_batch_id: str,
    body: AggregateMatchIsotopeFilteredDataBody,
):
    # Verify the existance of sample batch
    sample_batch = await get_sample_batch(sample_batch_id)
    sample_batch_name = sample_batch["sample_batch_name"]

    data = await aggregate_match_isotope_filtered_data(
        sample_batch_id=sample_batch_id,
        target_ion_id=body.target_ion_id,
        filter_params=body.filter_params,
        include_match_interference=body.include_match_interference,
    )
    if not data.empty:
        data_dict = data.to_dict("records")
        return {
            "results": len(data_dict),
            "message": (
                f"Filtered match isotope data fetched successfully for batch '{sample_batch_name}'"
            ),
            "data": data_dict,
        }
    return {
        "results": 0,
        "message": f"No match isotope data found for batch '{sample_batch_name}'",
        "data": [],
    }


@match_aggregate_batch_router.post("/api/match/aggregate/batch/{sample_batch_id}")
@api_route()
async def aggregate_batch_matches_route(
    sample_batch_id: str,
    body: AggregateMatchIsotopeFilteredDataBody,
):
    # Verify the existance of sample batch
    sample_batch = await get_sample_batch(sample_batch_id)
    sample_batch_name = sample_batch["sample_batch_name"]

    result = await aggregate_matches(
        sample_batch_id=sample_batch_id,
        target_ion_id=body.target_ion_id,
        filter_params=body.filter_params,
    )
    if result.get("results", 0) == 0:
        message = f"No match data found for batch '{sample_batch_name}'"
    else:
        message = f"Match data aggregated successfully for batch '{sample_batch_name}'"

    return {
        "message": message,
        "results": result.get("results", 0),
        "data": result.get("data", []),
    }


@match_aggregate_batch_router.post("/api/match/aggregate/batch/{sample_batch_id}/save")
@api_route()
async def aggregate_and_create_batch_matches_route(
    sample_batch_id: str,
    body: AggregateAndCreateMatchesBody,
):
    result = await aggregate_and_create_matches(
        sample_batch_id=sample_batch_id,
        target_ion_id=body.target_ion_id,
        filter_params=body.filter_params,
        match_ions=body.match_ions,
        match_compounds=body.match_compounds,
        match_collections=body.match_collections,
        match_samples=body.match_samples,
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


@match_aggregate_batch_router.post(
    "/api/match/aggregate/batch/{sample_batch_id}/resave"
)
@api_route()
async def aggregate_and_recreate_matches_route(
    sample_batch_id: str,
    body: AggregateAndCreateMatchesBody,
):
    result = await aggregate_and_recreate_matches(
        sample_batch_id=sample_batch_id,
        target_ion_id=body.target_ion_id,
        filter_params=body.filter_params,
        match_ions=body.match_ions,
        match_compounds=body.match_compounds,
        match_collections=body.match_collections,
        match_samples=body.match_samples,
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


@match_aggregate_batch_router.get("/api/match/aggregate/batch/{sample_batch_id}/all")
@api_route()
async def get_batch_and_aggregated_matches_route(
    sample_batch_id: str,
):
    return await get_batch_and_aggregated_matches(sample_batch_id=sample_batch_id)
