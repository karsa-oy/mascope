from fastapi import APIRouter, Depends
from mascope_backend.api.lib.api_features import api_route
from mascope_backend.api.lib.exceptions.api_exceptions import ApiException
from mascope_backend.api.controllers.match.aggregate.match_aggregate_controller import (
    aggregate_matches,
    aggregate_match_isotope_filtered_data,
    aggregate_and_create_matches,
    aggregate_and_recreate_matches,
)
from mascope_backend.api.controllers.match.aggregate.batch.match_aggregate_batch_controller import (
    get_batch_and_aggregated_matches,
)
from mascope_backend.api.controllers.sample.batches.sample_batches_controller import (
    get_sample_batch,
)
from mascope_backend.api.models.match.aggregate.match_aggregate_pydantic_model import (
    AggregateMatchIsotopeFilteredDataBody,
    AggregateAndCreateMatchesBody,
)
from mascope_backend.api.new.auth.dependencies import editor_user, guest_user


match_aggregate_batch_router = APIRouter(
    prefix="/api/match/aggregate/batch",
    tags=["Match Aggregate Batch"],
)


@match_aggregate_batch_router.post("/{sample_batch_id}/isotope")
@api_route()
async def aggregate_batch_match_isotope_filtered_data_route(
    sample_batch_id: str,
    body: AggregateMatchIsotopeFilteredDataBody,
    user=Depends(guest_user),
):
    """Fetch filtered match isotope data for a specific sample batch.

    :param sample_batch_id: The unique identifier of the sample batch.
    :type sample_batch_id: str
    :param body: Filter parameters for match isotope data.
    :type body: AggregateMatchIsotopeFilteredDataBody
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: Filtered isotope match data with count and message.
    :rtype: dict
    """
    # Verify the existance of sample batch
    sample_batch_result = await get_sample_batch(sample_batch_id)
    sample_batch = sample_batch_result.get("data")
    sample_batch_name = sample_batch["sample_batch_name"]

    data = await aggregate_match_isotope_filtered_data(
        sample_batch_id=sample_batch_id,
        target_ion_id=body.target_ion_id,
        match_params=body.match_params,
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


@match_aggregate_batch_router.post("/{sample_batch_id}")
@api_route()
async def aggregate_batch_matches_route(
    sample_batch_id: str,
    body: AggregateMatchIsotopeFilteredDataBody,
    user=Depends(guest_user),
):
    """Aggregate match data for a specific sample batch.

    :param sample_batch_id: The unique identifier of the sample batch.
    :type sample_batch_id: str
    :param body: Aggregation parameters for match data.
    :type body: AggregateMatchIsotopeFilteredDataBody
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: Aggregated match data with count and message.
    :rtype: dict
    """
    # Verify the existance of sample batch
    sample_batch_result = await get_sample_batch(sample_batch_id)
    sample_batch = sample_batch_result.get("data")
    sample_batch_name = sample_batch["sample_batch_name"]

    result = await aggregate_matches(
        sample_batch_id=sample_batch_id,
        target_ion_id=body.target_ion_id,
        match_params=body.match_params,
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


@match_aggregate_batch_router.post("/{sample_batch_id}/save")
@api_route()
async def aggregate_and_create_batch_matches_route(
    sample_batch_id: str,
    body: AggregateAndCreateMatchesBody,
    user=Depends(editor_user),
):
    """Aggregate and save new matches for a sample batch.

    :param sample_batch_id: The unique identifier of the sample batch.
    :type sample_batch_id: str
    :param body: Parameters for creating matches.
    :type body: AggregateAndCreateMatchesBody
    :param user: The current authenticated user with editor permissions.
    :type user: User
    :return: Success message and any associated logs.
    :rtype: dict
    """
    result = await aggregate_and_create_matches(
        sample_batch_id=sample_batch_id,
        target_ion_id=body.target_ion_id,
        match_params=body.match_params,
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


@match_aggregate_batch_router.post("/{sample_batch_id}/resave")
@api_route()
async def aggregate_and_recreate_matches_route(
    sample_batch_id: str,
    body: AggregateAndCreateMatchesBody,
    user=Depends(editor_user),
):
    """Recreate matches for a sample batch.

    :param sample_batch_id: The unique identifier of the sample batch.
    :type sample_batch_id: str
    :param body: Parameters for recreating matches.
    :type body: AggregateAndCreateMatchesBody
    :param user: The current authenticated user with editor permissions.
    :type user: User
    :return: Success message and any associated logs.
    :rtype: dict
    """
    result = await aggregate_and_recreate_matches(
        sample_batch_id=sample_batch_id,
        target_ion_id=body.target_ion_id,
        match_params=body.match_params,
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


@match_aggregate_batch_router.get("/{sample_batch_id}/all")
@api_route(token_access=True)
async def get_batch_and_aggregated_matches_route(
    sample_batch_id: str,
    user=Depends(guest_user),
):
    """Retrieve all batch and aggregated match data for a sample batch.
    May be used in the mascope_sdk lib for Jypter server.

    :param sample_batch_id: The unique identifier of the sample batch.
    :type sample_batch_id: str
    :param user: The current authenticated user, defaults to Depends(guest_user).
    :type user: User
    :return: Batch and aggregated match data.
    :rtype: dict
    """
    return await get_batch_and_aggregated_matches(sample_batch_id=sample_batch_id)
