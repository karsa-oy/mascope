from fastapi import APIRouter, BackgroundTasks, Request
from mascope_server.db.id import gen_id
from mascope_server.api.utils.api_features import api_route
from mascope_server.api.exceptions import ApiException
from mascope_server.api.controllers.match.match_aggregate_controller import (
    aggregate_matches,
    filter_match_isotope_data,
    aggregate_and_create_matches,
    reaggregate_and_create_matches,
)
from mascope_server.api.controllers.sample_batches_controller import get_sample_batch
from mascope_server.api.controllers.sample_items_controller import get_sample_item
from mascope_server.api.models.pydantic_models.match_pydantic_model import (
    FilterMatchIsotopeDataBody,
    AggregateAndCreateMatchesBody,
)


match_aggreagate_router = APIRouter()


@match_aggreagate_router.post("/api/match/aggregate/sample/{sample_item_id}/isotope")
@api_route()
async def filter_sample_match_isotope_data_route(
    sample_item_id: str,
    body: FilterMatchIsotopeDataBody,
):
    # Verify the existance of sample item
    sample = await get_sample_item(sample_item_id)
    sample_item_name = sample["sample_item_name"]

    data = await filter_match_isotope_data(
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


@match_aggreagate_router.post("/api/match/aggregate/sample/{sample_item_id}")
@api_route()
async def aggregate_sample_matches_route(
    sample_item_id: str,
    body: FilterMatchIsotopeDataBody,
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


@match_aggreagate_router.post("/api/match/aggregate/sample/{sample_item_id}/save")
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


@match_aggreagate_router.post("/api/match/aggregate/batch/{sample_batch_id}/isotope")
@api_route()
async def filter_batch_match_isotope_data_route(
    sample_batch_id: str,
    body: FilterMatchIsotopeDataBody,
):
    # Verify the existance of sample batch
    sample_batch = await get_sample_batch(sample_batch_id)
    sample_batch_name = sample_batch["sample_batch_name"]

    data = await filter_match_isotope_data(
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


@match_aggreagate_router.post("/api/match/aggregate/batch/{sample_batch_id}")
@api_route()
async def aggregate_batch_matches_route(
    sample_batch_id: str,
    body: FilterMatchIsotopeDataBody,
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


@match_aggreagate_router.post("/api/match/aggregate/batch/{sample_batch_id}/save")
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


@match_aggreagate_router.post("/api/match/reaggregate/batch/{sample_batch_id}/save")
@api_route()
async def reaggregate_and_create_batch_matches_route(
    sample_batch_id: str,
    body: AggregateAndCreateMatchesBody,
):
    result = await reaggregate_and_create_matches(
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
