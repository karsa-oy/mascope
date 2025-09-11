from fastapi import APIRouter, Depends
from mascope_backend.api.lib.api_features import api_route
from mascope_backend.api.controllers.match.aggregate.match_aggregate_controller import (
    aggregate_match_isotope_filtered_data,
    aggregate_matches,
    aggregate_and_create_matches,
)
from mascope_backend.api.controllers.match.aggregate.sample.match_aggregate_sample_controller import (
    aggregate_sample_match_ion,
    aggregate_sample_match_compound,
    aggregate_sample_match_compounds,
    get_sample_and_aggregated_matches,
)
from mascope_backend.api.controllers.sample.items.sample_items_controller import (
    get_sample_item,
)
from mascope_backend.api.models.match.aggregate.match_aggregate_pydantic_model import (
    AggregateMatchIsotopeFilteredDataBody,
    AggregateSampleMatchIonBody,
    AggregateSampleMatchCompoundBody,
    AggregateSampleMatchCompoundsBody,
    AggregateAndCreateMatchesBody,
)
from mascope_backend.api.new.auth.dependencies import editor_user, guest_user


match_aggregate_sample_router = APIRouter(
    prefix="/api/match/aggregate/sample",
    tags=["Match Aggregate Sample"],
)


@match_aggregate_sample_router.post("/{sample_item_id}/isotope")
@api_route()
async def aggregate_sample_match_isotope_filtered_data_route(
    sample_item_id: str,
    body: AggregateMatchIsotopeFilteredDataBody,
    user=Depends(guest_user),
):
    """Fetch filtered match isotope data for a specific sample.

    :param sample_item_id: The unique identifier of the sample.
    :type sample_item_id: str
    :param body: Filter parameters for match isotope data.
    :type body: AggregateMatchIsotopeFilteredDataBody
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: Filtered isotope match data with count and message.
    :rtype: dict
    """
    # Verify the existance of sample item
    sample_data = await get_sample_item(sample_item_id)
    sample = sample_data.get("data")
    sample_item_name = sample["sample_item_name"]

    data = await aggregate_match_isotope_filtered_data(
        sample_item_id=sample_item_id,
        target_ion_id=body.target_ion_id,
        match_params=body.match_params,
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


@match_aggregate_sample_router.post("/{sample_item_id}/ion")
@api_route()
async def aggregate_sample_match_ion_route(
    sample_item_id: str,
    body: AggregateSampleMatchIonBody,
    user=Depends(guest_user),
):
    """Aggregate match ion data for a specific sample.

    :param sample_item_id: The unique identifier of the sample.
    :type sample_item_id: str
    :param body: Aggregation parameters for match ion data.
    :type body: AggregateSampleMatchIonBody
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: Aggregated match ion data.
    :rtype: dict
    """
    return await aggregate_sample_match_ion(
        sample_item_id=sample_item_id,
        target_ion_id=body.target_ion_id,
        target_collection_id=body.target_collection_id,
        match_params=body.match_params,
    )


@match_aggregate_sample_router.post("/{sample_item_id}/compound")
@api_route(token_access=True)
async def aggregate_sample_match_compound_route(
    sample_item_id: str,
    body: AggregateSampleMatchCompoundBody,
    user=Depends(guest_user),
):
    """Aggregate match data for compounds within a sample based on a target compound formula,
    applying specified match parameters to filter the matches.

    :param sample_item_id: The unique identifier of the sample.
    :type sample_item_id: str
    :param body: Aggregation parameters for match compound data.
    :type body: AggregateSampleMatchCompoundBody
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: Aggregated match compound data.
    :rtype: dict
    """
    return await aggregate_sample_match_compound(
        sample_item_id=sample_item_id,
        target_compound_formula=body.target_compound.target_compound_formula,
        target_compound_name=body.target_compound.target_compound_name,
        match_params=body.match_params,
    )


@match_aggregate_sample_router.post("/{sample_item_id}/compounds")
@api_route(token_access=True)
async def aggregate_sample_match_compounds_route(
    sample_item_id: str,
    body: AggregateSampleMatchCompoundsBody,
    user=Depends(guest_user),
):
    """Aggregate match data for compounds within a sample based on a target compound formula,
    applying specified match parameters to filter the matches.

    :param sample_item_id: The unique identifier of the sample.
    :type sample_item_id: str
    :param body: Aggregation parameters for match compound data.
    :type body: AggregateSampleMatchCompoundBody
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: Aggregated match compound data.
    :rtype: dict
    """
    return await aggregate_sample_match_compounds(
        sample_item_id=sample_item_id,
        target_compound_formulas=body.target_compound_formulas,
        match_params=body.match_params,
        ion_mechanism_ids=body.ion_mechanism_ids,
    )


@match_aggregate_sample_router.post("/{sample_item_id}")
@api_route()
async def aggregate_sample_matches_route(
    sample_item_id: str,
    body: AggregateMatchIsotopeFilteredDataBody,
    user=Depends(guest_user),
):
    """Aggregate match data for a specific sample.

    :param sample_item_id: The unique identifier of the sample.
    :type sample_item_id: str
    :param body: Aggregation parameters for match data.
    :type body: AggregateMatchIsotopeFilteredDataBody
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: Aggregated match data with count and message.
    :rtype: dict
    """
    # Verify the existance of sample item
    sample_data = await get_sample_item(sample_item_id)
    sample = sample_data.get("data")
    sample_item_name = sample["sample_item_name"]

    result = await aggregate_matches(
        sample_item_id=sample_item_id,
        target_ion_id=body.target_ion_id,
        match_params=body.match_params,
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


@match_aggregate_sample_router.post("/{sample_item_id}/save")
@api_route(status_code=201)
async def aggregate_and_create_sample_matches_route(
    sample_item_id: str,
    body: AggregateAndCreateMatchesBody,
    user=Depends(editor_user),
):
    """Aggregate and save new matches for a sample.

    :param sample_item_id: The unique identifier of the sample.
    :type sample_item_id: str
    :param body: Parameters for creating matches.
    :type body: AggregateAndCreateMatchesBody
    :param user: The current authenticated user with editor permissions.
    :type user: User
    :return: Success message and any associated logs.
    :rtype: dict
    """
    result = await aggregate_and_create_matches(
        sample_item_id=sample_item_id,
        target_ion_id=body.target_ion_id,
        match_params=body.match_params,
    )

    return {
        "status": result.get("status"),
        "message": result.get("message", ""),
    }


@match_aggregate_sample_router.get("/{sample_item_id}/all")
@api_route()
async def get_sample_aggregate_matches_route(
    sample_item_id: str,
    user=Depends(guest_user),
):
    """Retrieve all sample and aggregated match data for a sample.

    :param sample_item_id: The unique identifier of the sample.
    :type sample_item_id: str
    :param user: The current authenticated user with guest permissions.
    :type user: User
    :return: Sample and aggregated match data.
    :rtype: dict
    """
    sample_data = await get_sample_and_aggregated_matches(sample_item_id=sample_item_id)
    if sample_data and sample_data.get("matched", 0) > 0:
        message = "Sample and match information retrieved successfully"
    else:
        message = "Sample retrieved successfully, no matches found for the sample"

    return {
        "message": message,
        "data": sample_data,
    }
