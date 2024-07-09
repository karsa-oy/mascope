import pandas as pd
from typing import Optional
from mascope_server.api.utils.api_features import api_controller
from mascope_server.api.controllers.sample_batches_controller import get_sample_batch
from mascope_server.api.controllers.target_collections_controller import (
    get_target_collections,
)
from mascope_server.api.controllers.target_compounds_controller import (
    get_target_compounds,
)
from mascope_server.api.controllers.target_ions_controller import (
    get_target_ions,
)
from mascope_server.api.controllers.target_isotopes_controller import (
    get_target_isotopes,
)


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
    target_ions = await get_target_ions(
        sample_batch_id=sample_batch_id,
        target_compound_id=target_compound_id,
        target_collection_id=target_collection_id,
        show_target_collection=True,
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
        # show_filter_params=True,
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
