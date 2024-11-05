from typing import Optional
from mascope_server.db import async_session
from mascope_server.db.models import (
    SampleBatch,
)
from mascope_server.api.lib.api_features import api_controller
from mascope_server.api.lib.exceptions.api_exceptions import NotFoundException
from mascope_server.api.controllers.sample.batches.sample_batches_controller import (
    get_sample_batch,
)
from mascope_server.api.controllers.samples.samples_controller import get_samples
from mascope_server.api.controllers.match.compounds.match_compounds_controller import (
    get_match_compounds,
)
from mascope_server.api.controllers.match.ions.match_ions_controller import (
    get_match_ions,
)
from mascope_server.api.controllers.match.isotopes.match_isotopes_controller import (
    get_match_isotopes,
)
from mascope_server.api.controllers.match.interferences.match_interferences_controller import (
    get_match_interferences,
)
from mascope_server.api.controllers.target.collections.target_collections_controller import (
    get_target_collections,
)
from mascope_server.api.controllers.target.compounds.target_compounds_controller import (
    get_target_compounds,
)
from mascope_server.api.controllers.target.ions.target_ions_controller import (
    get_target_ions,
)
from mascope_server.api.controllers.target.isotopes.target_isotopes_controller import (
    get_target_isotopes,
)


@api_controller()
async def get_batch_data(
    sample_batch_id: str,
) -> dict:
    """
    Retrieve detailed data for all samples in a batch, including compounds, ions, and isotopes.

    This function fetches all samples in a batch and retrieves combined data for
    compounds, ions, isotopes, match interferences, and samples, optionally applying deduplication
    based on collection priority.

    This function is used in the `mascope_api` library, serving as a wrapper for Jupyter
    notebooks, enabling easy retrieval of batch match data in batch selector widgets.

    Steps:
    1. Fetch the sample batch using the provided sample batch ID.
    2. Fetch all the samples within the batch.
    3. Retrieve samples and targets joined with match data - compounds, ions, isotopes and interferences for the batch.
    4. Merge match interference data into the match isotopes.
    5. Combine all match data and prepare a structured response.

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
                    "isotopes": [],  # combination of match_isotopes, match_interferences, and target_isotopes
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

        match_interferences_result = await get_match_interferences(
            sample_batch_id=sample_batch_id
        )
        match_interferences = match_interferences_result.get("data", [])

        # Step 4: Merge sample_peak_interference into isotopes
        # Create a mapping from (sample_item_id, target_isotope_id) to sample_peak_interference
        match_interferences_dict = {
            (
                interference["sample_item_id"],
                interference["target_isotope_id"],
            ): interference["sample_peak_interference"]
            for interference in match_interferences
        }

        # Update isotopes with sample_peak_interference
        for isotope in isotopes:
            key = (isotope["sample_item_id"], isotope["target_isotope_id"])
            sample_peak_interference = match_interferences_dict.get(key, None)
            isotope["sample_peak_interference"] = sample_peak_interference

        # Step 5: Add sample_batch_name to each sample
        for sample in samples:
            sample["sample_batch_name"] = sample_batch.sample_batch_name

        # Step 6: Prepare the final output
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


@api_controller()
async def get_match_batch_collections(
    sample_batch_id: str,
    order: Optional[str] = None,
    page: int = 0,
    limit: int = 10000,
):
    # Verify the existance of sample batch
    sample_batch = await get_sample_batch(sample_batch_id)
    sample_batch_name = sample_batch["sample_batch_name"]

    # Fetch target collections for the sample batch
    target_collections = await get_target_collections(
        sample_batch_id=sample_batch_id,
    )
    if not target_collections["data"]:
        return {
            "results": 0,
            "message": f"No target collections found for batch '{sample_batch_name}'.",
            "data": [],
        }

    #  Placeholder for match batch aggregation logic

    # # Fetch match collections for the sample batch
    # match_collections = await get_match_collections(
    #     sample_item_id=sample_item_id,
    # )

    # # Merging: Combine target collections data with match collections data
    match_data = {
        # item["target_collection_id"]: item for item in match_collections["data"]
    }
    match_batch_collections = []
    for collection in target_collections["data"]:
        collection.update(
            match_data.get(
                collection["target_collection_id"],
                {
                    "match_collection_id": None,
                    "match_score": None,
                    "match_category": None,
                    "sample_peak_area_sum": None,
                    "sample_peak_interference_sum": None,
                    "match_collection_utc_created": None,
                    "match_collection_utc_modified": None,
                },
            )
        )
        match_batch_collections.append(collection)

    # Sorting and pagination logic
    match_batch_collections_sorted = sorted(
        match_batch_collections,
        key=lambda x: (
            x["target_collection_id"],
            x["match_category"],
            x["match_score"],
        ),
        reverse=(order == "desc"),
    )
    match_batch_collections_paginated = match_batch_collections_sorted[
        page * limit : (page + 1) * limit
    ]

    return {
        "results": len(match_batch_collections_sorted),
        "message": f"Successfully retrieved target collection matches for batch '{sample_batch_name}'.",
        "data": match_batch_collections_paginated,
    }


@api_controller()
async def get_match_batch_compounds(
    sample_batch_id: str,
    target_collection_id: Optional[str] = None,
    order: Optional[str] = None,
    page: int = 0,
    limit: int = 10000,
):
    # Verify the existance of sample batch
    sample_batch = await get_sample_batch(sample_batch_id)
    sample_batch_name = sample_batch["sample_batch_name"]

    # Fetch target compounds for the sample batch with potential duplicates across collections
    target_compounds = await get_target_compounds(
        sample_batch_id=sample_batch_id,
        target_collection_id=target_collection_id,
        show_target_collection=True,
    )

    #  Placeholder for match batch aggregation logic

    # # Fetch match compounds for the sample batch with collection details
    # match_compounds = await get_match_compounds(
    #     sample_batch_id=sample_batch_id,
    # )

    if not target_compounds["data"]:
        return {
            "results": 0,
            "message": f"No target compounds found for batch '{sample_batch_name}'.",
            "data": [],
        }

    # Merging: Combine target compounds data with match compounds data
    match_data = {
        # item["target_compound_id"]: item for item in match_compounds["data"]
    }
    match_batch_compounds = []
    for compound in target_compounds["data"]:
        compound.update(
            match_data.get(
                compound["target_compound_id"],
                {
                    "match_compound_id": None,
                    "match_score": None,
                    "match_category": None,
                    "sample_peak_area_sum": None,
                    "sample_peak_interference_sum": None,
                    "match_compound_utc_created": None,
                    "match_compound_utc_modified": None,
                },
            )
        )
        match_batch_compounds.append(compound)

    # Sorting and pagination logic
    match_batch_compounds_sorted = sorted(
        match_batch_compounds,
        key=lambda x: (
            x["target_collection_id"],
            x["match_category"],
            x["match_score"],
        ),
        reverse=(order == "desc"),
    )
    match_batch_compounds_paginated = match_batch_compounds_sorted[
        page * limit : (page + 1) * limit
    ]

    return {
        "results": len(match_batch_compounds_sorted),
        "message": f"Successfully retrieved target compound matches for batch '{sample_batch_name}'.",
        "data": match_batch_compounds_paginated,
    }


@api_controller()
async def get_match_batch_ions(
    sample_batch_id: str,
    target_compound_id: Optional[str] = None,
    target_collection_id: Optional[str] = None,
    order: Optional[str] = None,
    page: int = 0,
    limit: int = 10000,
):
    # Verify the existance of sample batch
    sample_batch = await get_sample_batch(sample_batch_id)
    sample_batch_name = sample_batch["sample_batch_name"]

    # Fetch target ions with filters:
    #   - sample_batch_id - target_ions for the sample batch (unique)
    #   - target_compound_id - target_ions for particular target_compound (unique)
    #   - target_collection_id - target_ions for particular target_collection (unique)
    #   - show_target_collection - add target collection id and adds potential compount duplicates
    #   - show_ionization_mechanism - add ionization mechanism details
    target_ions = await get_target_ions(
        sample_batch_id=sample_batch_id,
        target_compound_id=target_compound_id,
        target_collection_id=target_collection_id,
        show_target_collection=True,
        show_ionization_mechanism=True,
    )
    if not target_ions["data"]:
        return {
            "results": 0,
            "message": f"No target ions found for batch '{sample_batch_name}'.",
            "data": [],
        }

    #  Placeholder for match batch aggregation logic

    # Fetch match ions for the sample batch with collection details
    # match_ions = await get_match_ions(
    #     sample_item_id=sample_item_id,
    # )

    # Merging: Combine target ions data with match ions data
    match_data = {
        # item["target_ion_id"]: item for item in match_ions["data"]
    }
    match_batch_ions = []
    for ion in target_ions["data"]:
        ion.update(
            match_data.get(
                ion["target_ion_id"],
                {
                    "match_ion_id": None,
                    "match_score": None,
                    "match_category": None,
                    "sample_peak_area_sum": None,
                    "sample_peak_interference_sum": None,
                    "match_ion_utc_created": None,
                    "match_ion_utc_modified": None,
                },
            )
        )
        match_batch_ions.append(ion)

    # Sorting and pagination logic
    match_batch_ions_sorted = sorted(
        match_batch_ions,
        key=lambda x: (
            x.get("target_collection_id", ""),
            x.get("match_category", 0),
            x.get("match_score", 0),
        ),
        reverse=(order == "desc"),
    )
    match_batch_ions_paginated = match_batch_ions_sorted[
        page * limit : (page + 1) * limit
    ]

    return {
        "results": len(match_batch_ions_sorted),
        "message": f"Successfully retrieved target ion matches for batch '{sample_batch_name}'.",
        "data": match_batch_ions_paginated,
    }


@api_controller()
async def get_match_batch_isotopes(
    sample_batch_id: str,
    target_ion_id: Optional[str] = None,
    min_relative_abundance: Optional[str] = None,
    target_collection_id: Optional[str] = None,
    order: Optional[str] = None,
    page: int = 0,
    limit: int = 10000,
):
    # Verify the existance of sample batch
    sample_batch = await get_sample_batch(sample_batch_id)
    sample_batch_name = sample_batch["sample_batch_name"]

    # Fetch target isotopes for the sample batch with filter parameters
    target_isotopes = await get_target_isotopes(
        target_ion_id=target_ion_id,
        min_relative_abundance=min_relative_abundance,
        sample_batch_id=sample_batch_id,
        target_collection_id=target_collection_id,
        show_target_collection=True,
        # show_match_params=True,
    )
    if not target_isotopes["data"]:
        return {
            "results": 0,
            "message": f"No target isotopes found for batch '{sample_batch_name}'.",
            "data": [],
        }

    #  Placeholder for match batch aggregation logic

    # Fetch match isotopes and interferences for the sample item
    # match_isotopes = await get_match_isotopes(sample_item_id=sample_item_id)
    # match_interferences = await get_match_interferences(sample_item_id=sample_item_id)
    match_isotopes_data = {
        # item["target_isotope_id"]: item for item in match_isotopes["data"]
    }
    match_interferences_data = {
        # item["target_isotope_id"]: item for item in match_interferences["data"]
    }

    # Merge target isotopes with match isotopes data
    match_batch_isotopes = []
    for isotope in target_isotopes["data"]:
        match_isotope_data = match_isotopes_data.get(
            isotope["target_isotope_id"],
            {
                "match_score": None,
                "match_category": None,
            },
        )
        isotope.update(match_isotope_data)
        match_interference_data = match_interferences_data.get(
            isotope["target_isotope_id"],
            {
                "sample_peak_interference": None,
            },
        )
        isotope.update(match_interference_data)
        match_batch_isotopes.append(isotope)

    # Sorting and pagination logic
    match_batch_isotopes_sorted = sorted(
        match_batch_isotopes,
        key=lambda x: (
            x.get("target_collection_id", ""),
            x.get("match_category", 0),
            x.get("match_score", 0),
        ),
        reverse=(order == "desc"),
    )
    match_batch_isotopes_paginated = match_batch_isotopes_sorted[
        page * limit : (page + 1) * limit
    ]

    return {
        "results": len(match_batch_isotopes_sorted),
        "message": f"Successfully retrieved target isotopes matches for batch '{sample_batch_name}'.",
        "data": match_batch_isotopes_paginated,
    }
