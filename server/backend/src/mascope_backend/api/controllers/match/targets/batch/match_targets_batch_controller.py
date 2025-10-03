from typing import Optional
from mascope_backend.db import async_session
from mascope_backend.db.models import (
    SampleBatch,
)
from mascope_backend.api.lib.api_features import api_controller
from mascope_backend.api.lib.exceptions.api_exceptions import NotFoundException
from mascope_backend.api.controllers.samples.samples_controller import get_samples
from mascope_backend.api.controllers.match.compounds.match_compounds_controller import (
    get_match_compounds,
)
from mascope_backend.api.controllers.match.ions.match_ions_controller import (
    get_match_ions,
)
from mascope_backend.api.controllers.match.isotopes.match_isotopes_controller import (
    get_match_isotopes,
)


@api_controller()
async def get_batch_data(
    sample_batch_id: str,
) -> dict:
    """
    Retrieve detailed data for all samples in a batch, including compounds, ions, and isotopes.

    This function fetches all samples in a batch and retrieves combined data for
    compounds, ions, isotopes, and samples, optionally applying deduplication
    based on collection priority.

    This function is used in the `mascope_sdk` library, serving as a wrapper for Jupyter
    notebooks, enabling easy retrieval of batch match data in batch selector widgets.

    Steps:
    1. Fetch the sample batch using the provided sample batch ID.
    2. Fetch all the samples within the batch.
    3. Retrieve samples and targets joined with match data - compounds, ions, isotopes for the batch.
    4. Combine all match data and prepare a structured response.

    :param sample_batch_id: Unique identifier of the sample batch.
    :type sample_batch_id: str
    :raises NotFoundException: If the sample batch with the specified item ID is not found.
    :return: A dictionary containing the batch information, samples and combined target/match data for compounds, ions, and isotopes.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Fetch the sample batch to verify its existence
        sample_batch = await session.get(SampleBatch, sample_batch_id)
        if not sample_batch:
            raise NotFoundException(
                f"Sample batch with ID '{sample_batch_id}' not found."
            )

        # Step 2: Fetch all samples within the batch
        sample_results = await get_samples(sample_batch_id=sample_batch_id)
        samples = sample_results.get("data", [])

        if not samples:
            return {
                "message": f"No samples found for sample batch '{sample_batch.sample_batch_name}'.",
                "result": {
                    "samples": 0,
                    "compounds": 0,
                    "ions": 0,
                    "isotopes": 0,
                },
                "data": {
                    "sample_batch": sample_batch.to_dict(),
                    "samples": [],  # combination of samples (sample_item + sample_file) and match_samples
                    "compounds": [],  # combination of match_compounds and target_compounds
                    "ions": [],  # combination of match_ions and target_ions
                    "isotopes": [],  # combination of match_isotopes and target_isotopes
                },
            }

        # Step 3: Fetch match data joined with targets for the batch using sample_batch_id
        match_compounds_result = await get_match_compounds(
            sample_batch_id=sample_batch_id,
            show_target_compound=True,
        )
        compounds = match_compounds_result.get("data", [])

        match_ions_result = await get_match_ions(
            sample_batch_id=sample_batch_id,
            show_target_ion=True,
            show_ionization_mechanism=True,
        )
        ions = match_ions_result.get("data", [])

        match_isotopes_result = await get_match_isotopes(
            sample_batch_id=sample_batch_id,
            show_target_isotope=True,
        )
        isotopes = match_isotopes_result.get("data", [])

        # Add sample_batch_name to each sample
        for sample in samples:
            sample["sample_batch_name"] = sample_batch.sample_batch_name

        # Step 4: Prepare the final output
        message = f"Successfully retrieved data for sample batch '{sample_batch.sample_batch_name}'."

        return {
            "message": message,
            "result": {
                "samples": len(samples),
                "compounds": len(compounds),
                "ions": len(ions),
                "isotopes": len(isotopes),
            },
            "data": {
                "sample_batch": sample_batch.to_dict(),
                "samples": samples,
                "compounds": compounds,
                "ions": ions,
                "isotopes": isotopes,
            },
        }
