from mascope_server.db import async_session
from mascope_server.db.models import (
    SampleBatch,
)
from mascope_server.api.lib.api_features import api_controller
from mascope_server.api.lib.exceptions.api_exceptions import NotFoundException
from mascope_server.api.controllers.match.aggregate.match_aggregate_controller import (
    aggregate_matches,
)
from mascope_server.api.controllers.match.lib.match_compare import compare_match_samples
from mascope_server.api.controllers.samples.samples_controller import get_samples


@api_controller()
async def get_batch_and_aggregated_matches(
    sample_batch_id: str,
) -> dict:
    """
    Retrieves detailed information for a specific sample batch, including aggregated match data for isotopes, ions,
    compounds. This function is used in the `mascope_api` wrapper for Jupyter notebooks to load
    the batch match data get_sample_batch_data_new, that is used in the batch selector widget.

    Steps:
    1. Fetch the sample batch using the provided sample batch ID to ensure it exists.
    2. Aggregate match data for the batch, including isotopes, ions, compounds, and collections, using the new aggregation controllers.
    3. If no match data is found, return a message indicating the absence of match data.
    4. Fetch detailed sample data and compare match data fields.
    5. Prepare the final output, including the batch data, match details, and mismatch info, and return it in a structured dictionary format.

    :param sample_batch_id: Unique identifier for the sample batch.
    :type sample_batch_id: str
    :raises NotFoundException: If the sample batch with the specified item ID is not found.
    :return: A dictionary containing the batch information, aggregated match data, and mismatch information.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Fetch the sample batch to verify its existence
        sample_batch = await session.get(SampleBatch, sample_batch_id)
        if not sample_batch:
            raise NotFoundException(
                f"Sample batch with ID '{sample_batch_id}' not found"
            )

        # Step 2: Aggregate the match data using the new aggregation controllers
        aggregated_result = await aggregate_matches(
            sample_batch_id=sample_batch_id, match_isotopes=True
        )

        if aggregated_result.get("results", 0) == 0:
            message = f"No match data found for sample batch '{sample_batch.sample_batch_name}'"
            return {
                "message": message,
            }

        # Step 3: Unpack the aggregated match data
        match_data = aggregated_result.get("data", {})
        match_isotopes = match_data.get("match_isotopes", [])
        match_ions = match_data.get("match_ions", [])
        match_compounds = match_data.get("match_compounds", [])
        match_samples = match_data.get("match_samples", [])

        # Step 4: Fetch detailed sample data
        sample_results = await get_samples(sample_batch_id=sample_batch_id)
        samples = sample_results.get("data", [])

        # Add the sample_batch_name to each sample
        for sample in samples:
            sample["sample_batch_name"] = sample_batch.sample_batch_name

        # Step 5: Compare match sample data and gather mismatch information
        mismatch_info = compare_match_samples(samples, match_samples)

        # Step 6: Prepare the final output
        message = f"Data aggregation for sample batch '{sample_batch.sample_batch_name}' completed successfully."
        if len(mismatch_info) != 0:
            message = f"Data aggregation for sample batch '{sample_batch.sample_batch_name}' completed with mismatches found in {len(mismatch_info)} samples match data."

        return {
            "message": message,
            "result": {
                "samples": len(samples),
                "match_isotopes": len(match_isotopes),
                "match_ions": len(match_ions),
                "match_compounds": len(match_compounds),
                "match_samples": len(match_samples),
            },
            "data": {
                "sample_batch": sample_batch.to_dict(),
                "samples": samples,
                "match_samples": match_samples,
                "match_compounds": match_compounds,
                "match_ions": match_ions,
                "match_isotopes": match_isotopes,
            },
        }
