from typing import Optional

import pandas as pd

from mascope_file.name import get_instrument_type

from mascope_backend.api.lib.api_features import api_controller
from mascope_backend.api.controllers.samples.samples_controller import get_sample
from mascope_backend.api.controllers.sample.items.sample_items_controller import (
    get_sample_item,
)
from mascope_backend.api.controllers.target.collections.target_collections_controller import (
    get_target_collections,
)
from mascope_backend.api.controllers.target.compounds.target_compounds_controller import (
    get_target_compounds,
)
from mascope_backend.api.controllers.target.ions.target_ions_controller import (
    get_target_ions,
)
from mascope_backend.api.controllers.target.isotopes.target_isotopes_controller import (
    get_target_isotopes,
)
from mascope_backend.api.controllers.match.collections.match_collections_controller import (
    get_match_collections,
)
from mascope_backend.api.controllers.match.compounds.match_compounds_controller import (
    get_match_compounds,
)
from mascope_backend.api.controllers.match.ions.match_ions_controller import (
    get_match_ions,
)
from mascope_backend.api.controllers.match.isotopes.match_isotopes_controller import (
    get_match_isotopes,
)
from mascope_backend.api.new.match.params import apply_match_params
from mascope_backend.api.controllers.match.lib.match_util import (
    deduplicate_match_df,
    sort_and_paginate_match_sample_df,
)
from mascope_match.params import (
    DEFAULT_MIN_ISOTOPE_ABUNDANCE,
)


@api_controller()
async def get_match_sample_collections(
    sample_item_id: str,
    order: Optional[str] = None,
    page: int = 0,
    limit: int = 10000,
) -> dict:
    """
    Retrieves a list of sample target collections joined with match collection data for a given sample item ID,
    optionally ordered by a specified field.

    Steps:
    1. Retrieve the sample item data including batch ID and name.
    2. Fetch target collections associated with the sample's batch.
    3. If no target collections are found, return a response indicating no data.
    4. Fetch matching collections based on the sample item ID.
    5. Merge target collection data with matched collection data.
    6. Sort the merged data based on the provided order criteria.
    7. Paginate the sorted data.
    8. Return the results along with a success message.

    :param sample_item_id: Unique identifier of the sample item.
    :type sample_item_id: str
    :param order: Column name to sort by, defaults to None.
    :type order: Optional[str], optional
    :param page: Page number for pagination, defaults to 0.
    :type page: int, optional
    :param limit: Number of items per page, defaults to 10000.
    :type limit: int, optional
    :return: A dictionary containing the count of results, a success message, and the paginated data.
    :rtype: dict
    """
    # Get sample item data
    sample_data = await get_sample_item(sample_item_id)
    sample = sample_data.get("data")
    sample_batch_id = sample["sample_batch_id"]
    sample_item_name = sample["sample_item_name"]

    # Fetch target collections for the sample batch
    target_collections = await get_target_collections(
        sample_batch_id=sample_batch_id,
    )
    if not target_collections["data"]:
        return {
            "results": 0,
            "message": f"No target collections found for sample '{sample_item_name}'.",
            "data": [],
        }

    # Fetch match collections for the sample item
    match_collections = await get_match_collections(
        sample_item_id=sample_item_id,
    )

    # Merging: Combine target collections data with match collections data
    match_collections_data = {
        item["target_collection_id"]: item for item in match_collections["data"]
    }
    match_sample_collections = []
    for collection in target_collections["data"]:
        collection.update(
            match_collections_data.get(
                collection["target_collection_id"],
                {
                    "match_collection_id": None,
                    "sample_item_id": sample_item_id,
                    "match_score": None,
                    "match_category": None,
                    "sample_peak_intensity_sum": None,
                    "match_collection_utc_created": None,
                    "match_collection_utc_modified": None,
                },
            )
        )
        match_sample_collections.append(collection)

    # Convert to pandas dataframe for sorting and pagination
    match_sample_collections_df = pd.DataFrame(match_sample_collections)

    # Sort and paginate the DataFrame
    match_sample_collections_df = sort_and_paginate_match_sample_df(
        match_sample_collections_df, order, page, limit
    )

    return {
        "message": f"Successfully retrieved target collections match data for sample '{sample_item_name}'.",
        "results": len(match_sample_collections_df),
        "data": match_sample_collections_df.to_dict(orient="records"),
    }


@api_controller()
async def get_match_sample_compounds(
    sample_item_id: str,
    target_collection_id: Optional[str] = None,
    deduplicate: bool = False,
    order: Optional[str] = None,
    page: int = 0,
    limit: int = 10000,
) -> dict:
    """
    Retrieves a list of sample target compounds joined with match compounds data for a given sample item ID,
    optionally filtered by target collection ID and ordered by a specified field.

    Steps:
    1. Retrieve the sample item data including batch ID and name.
    2. Fetch target compounds associated with the sample's batch, considering potential collection filters.
    3. If no target compounds are found, return a response indicating no data.
    4. Fetch matching compounds based on the sample item ID.
    5. Merge target compound data with matched compound data.
    6. Sort the merged data based on the provided order criteria.
    7. Paginate the sorted data.
    8. Return the results along with a success message.

    :param sample_item_id: Unique identifier of the sample item.
    :type sample_item_id: str
    :param target_collection_id: Filter compounds by target collection, defaults to None.
    :type target_collection_id: Optional[str], optional
    :param deduplicate: Flag to indicate whether compound deduplication should be applied.
    :type deduplicate: bool
    :param order: Column name to sort by, defaults to None.
    :type order: Optional[str], optional
    :param page: Page number for pagination, defaults to 0.
    :type page: int, optional
    :param limit: Number of items per page, defaults to 10000.
    :type limit: int, optional
    :return: A dictionary containing the count of results, a success message, and the paginated data.
    :rtype: dict
    """
    # Get sample item data
    sample_data = await get_sample_item(sample_item_id)
    sample = sample_data.get("data")
    sample_batch_id = sample["sample_batch_id"]
    sample_item_name = sample["sample_item_name"]

    # Fetch target compounds with filters:
    #   - sample_batch_id - target_compounds for the sample batch (unique)
    #   - target_collection_id - target_compounds for particular target_collection (unique)
    #   - show_target_collection - add target collection id and adds potential compound duplicates
    target_compounds = await get_target_compounds(
        sample_batch_id=sample_batch_id,
        target_collection_id=target_collection_id,
        show_target_collection=True,
    )
    if not target_compounds["data"]:
        return {
            "results": 0,
            "message": f"No target compounds found for sample '{sample_item_name}'.",
            "data": [],
        }

    # Fetch match compounds for the sample item with collection details
    match_compounds = await get_match_compounds(
        sample_item_id=sample_item_id,
    )

    # Merging: Combine target compounds data with match compounds data
    match_compounds_data = {
        item["target_compound_id"]: item for item in match_compounds["data"]
    }
    match_sample_compounds = []
    for compound in target_compounds["data"]:
        compound.update(
            match_compounds_data.get(
                compound["target_compound_id"],
                {
                    "match_compound_id": None,
                    "sample_item_id": sample_item_id,
                    "match_score": None,
                    "match_category": None,
                    "sample_peak_intensity_sum": None,
                    "match_compound_utc_created": None,
                    "match_compound_utc_modified": None,
                },
            )
        )
        match_sample_compounds.append(compound)

    # Convert to pandas dataframe for sorting and pagination
    match_sample_compounds_df = pd.DataFrame(match_sample_compounds)

    # Deduplicate if required
    if deduplicate:
        match_sample_compounds_df = deduplicate_match_df(
            match_sample_compounds_df, id_keys=("target_compound_id", "sample_item_id")
        )

    # Sort and paginate the DataFrame
    match_sample_compounds_df = sort_and_paginate_match_sample_df(
        match_sample_compounds_df, order, page, limit
    )

    return {
        "message": f"Successfully retrieved target compounds match data for sample '{sample_item_name}'.",
        "results": len(match_sample_compounds_df),
        "data": match_sample_compounds_df.to_dict(orient="records"),
    }


@api_controller()
async def get_match_sample_ions(
    sample_item_id: str,
    target_compound_id: Optional[str] = None,
    target_collection_id: Optional[str] = None,
    deduplicate: bool = False,
    order: Optional[str] = "desc",
    page: int = 0,
    limit: int = 10000,
) -> dict:
    """
    Retrieves a list of sample target ions joined with match ions data for a given sample item ID,
    and allows sorting and pagination of the results.
    All data returned is JSON compliant by replacing NaNs and NaTs with None and preserving the integer data type for 'match_category'.

    Steps:
    1. Fetching the sample item data from the database
    2. Retrieve target ions based on the sample batch ID and optional filters for compound and collection IDs.
    3. If no target ions are found, return a message indicating absence of data.
    4. Fetch matched ions data for the sample item ID.
    5. Merge target ions data with matched ions data.
    6. Sorting the merged data based on 'target_collection_id', 'match_category', and 'match_score'.
       Handles NaN values by treating them as zeros for sorting purposes but ensures that original NaN values are preserved in the output.
    7. Paginating the sorted data based on specified 'page' and 'limit' parameters.
    8. Return the paginated list of matched ions along with a success message.

    :param sample_item_id: Unique identifier of the sample item to fetch ions for.
    :type sample_item_id: str
    :param target_compound_id: Optional filter by target compound ID.
    :type target_compound_id: Optional[str], optional
    :param target_collection_id: Optional filter by target collection ID.
    :type target_collection_id: Optional[str], optional
    :param deduplicate: Flag to indicate whether ion deduplication should be applied.
    :type deduplicate: bool
    :param order: Sorting order ('asc' or 'desc'), default to 'desc'.
    :type order: Optional[str], optional
    :param page: Page number for pagination.
    :type page: int, optional
    :param limit: Number of items per page.
    :type limit: int, optional
    :return: A dictionary with the total results, a success message, and the list of matched ions.
    :rtype: dict
    """
    # Get sample item data
    sample_data = await get_sample_item(sample_item_id)
    sample = sample_data.get("data")
    sample_batch_id = sample["sample_batch_id"]
    sample_item_name = sample["sample_item_name"]

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
            "message": f"No target ions found for sample '{sample_item_name}'.",
            "data": [],
        }

    # Fetch match ions for the sample item with collection details
    match_ions = await get_match_ions(
        sample_item_id=sample_item_id,
    )

    # Merging: Combine target ions data with match ions data
    match_ions_data = {item["target_ion_id"]: item for item in match_ions["data"]}
    match_sample_ions = []
    for ion in target_ions["data"]:
        ion.update(
            match_ions_data.get(
                ion["target_ion_id"],
                {
                    "match_ion_id": None,
                    "sample_item_id": sample_item_id,
                    "match_score": None,
                    "match_category": None,
                    "sample_peak_intensity_sum": None,
                    "match_ion_utc_created": None,
                    "match_ion_utc_modified": None,
                },
            )
        )
        match_sample_ions.append(ion)

    # Convert to pandas dataframe for sorting and pagination
    match_sample_ions_df = pd.DataFrame(match_sample_ions)

    # Deduplicate if required
    if deduplicate:
        match_sample_ions_df = deduplicate_match_df(
            match_sample_ions_df, id_keys=("target_ion_id", "sample_item_id")
        )

    # Sort and paginate the DataFrame
    match_sample_ions_df = sort_and_paginate_match_sample_df(
        match_sample_ions_df, order, page, limit
    )

    return {
        "message": f"Successfully retrieved target ions match data for sample '{sample_item_name}'.",
        "results": len(match_sample_ions_df),
        "data": match_sample_ions_df.to_dict(orient="records"),
    }


@api_controller()
async def get_match_sample_isotopes(
    sample_item_id: str,
    target_ion_id: Optional[str] = None,
    min_relative_abundance: Optional[str] = DEFAULT_MIN_ISOTOPE_ABUNDANCE,
    target_collection_id: Optional[str] = None,
    deduplicate: bool = False,
    order: Optional[str] = "desc",
    page: int = 0,
    limit: int = 10000,
) -> dict:
    """
    Retrieves a list of sample target isotopes joined with match isotope data for a given sample item ID,
    and allows sorting and pagination of the results. All data manipulation is handled within DataFrames and that NaNs
    and NaTs are replaced with None for JSON serialization.

    Steps:
    1. Retrieve the sample item data, including batch ID, sample name, and instrument.
    2. Fetch target isotopes based on the filter parameters including batch, ion, and collection IDs.
    3. If no target isotopes are found, return a response indicating no data.
    4. Fetch matched isotopes based on the sample item ID.
    5. Merge target isotope data with matched isotopes.
    6. Add sample instrument data to each merged record.
    7. Apply filtering parameters to adjust the match score and categorize match data.
    8. Sort the filtered DataFrame based on 'target_collection_id', 'match_category', and 'match_score', handling NaNs appropriately.
    9. Paginate the sorted data and prepare it for output by replacing placeholders for absent data with None.
    10. Return the paginated data along with success or informative messages.

    :param sample_item_id: Unique identifier of the sample item.
    :type sample_item_id: str
    :param target_ion_id: Filter isotopes by target ion ID, defaults to None.
    :type target_ion_id: Optional[str], optional
    :param min_relative_abundance: Filter isotopes by minimum relative abundance, defaults to DEFAULT_MIN_ISOTOPE_ABUNDANCE.
    :type min_relative_abundance: Optional[str], optional
    :param target_collection_id: Filter isotopes by target collection ID, defaults to None.
    :type target_collection_id: Optional[str], optional
    :param deduplicate: Flag to indicate whether isotopes deduplication should be applied.
    :type deduplicate: bool
    :param order: Sorting order ('asc' or 'desc'), default to 'desc'.
    :type order: Optional[str], optional
    :param page: Page number for pagination, defaults to 0.
    :type page: int, optional
    :param limit: Number of items per page, defaults to 10000.
    :type limit: int, optional
    :return: A dictionary containing the count of results, success message, and the paginated data.
    :rtype: dict
    """
    # Get sample item data
    sample_data = await get_sample(sample_item_id)
    sample = sample_data.get("data")
    sample_batch_id = sample["sample_batch_id"]
    sample_item_name = sample["sample_item_name"]
    instrument = sample["instrument"]
    instrument_type = get_instrument_type(sample["filename"])
    isotope_resolution = "LOW" if instrument_type == "tof" else "HIGH"

    # Fetch target isotopes for the sample batch with filter parameters
    target_isotopes = await get_target_isotopes(
        target_ion_id=target_ion_id,
        min_relative_abundance=min_relative_abundance,
        resolution=isotope_resolution,
        sample_batch_id=sample_batch_id,
        target_collection_id=target_collection_id,
        show_target_collection=True,
        show_match_params=True,
    )
    if not target_isotopes["data"]:
        return {
            "results": 0,
            "message": f"No target isotopes found for sample '{sample_item_name}'.",
            "data": [],
        }
    # Fetch match isotopes for the sample item
    match_isotopes = await get_match_isotopes(sample_item_id=sample_item_id)
    match_isotopes_data = {
        item["target_isotope_id"]: item for item in match_isotopes["data"]
    }

    # Merge target isotopes with match isotopes data
    match_sample_isotopes = []
    for isotope in target_isotopes["data"]:
        match_isotope_data = match_isotopes_data.get(
            isotope["target_isotope_id"],
            {
                "match_isotope_id": None,
                "sample_item_id": sample_item_id,
                "sample_peak_id": None,
                "sample_peak_mz": None,
                "sample_peak_intensity": None,
                "sample_peak_intensity_relative": None,
                "sample_peak_tof": None,
                "match_abundance_error": None,
                "match_mz_error": None,
                "match_isotope_similarity": None,
                "match_score": None,
                "match_isotope_utc_created": None,
                "match_isotope_utc_modified": None,
            },
        )
        isotope.update(match_isotope_data)
        # Add instrument data to each record for filtering logic
        isotope["instrument"] = instrument
        match_sample_isotopes.append(isotope)

    # Convert to DataFrame for filtering
    match_sample_isotopes_df = pd.DataFrame(match_sample_isotopes)

    # Apply filtering to filter the match_score and assign match_category
    match_sample_isotopes_df = apply_match_params(match_sample_isotopes_df)

    # Deduplicate if required
    if deduplicate:
        match_sample_isotopes_df = deduplicate_match_df(
            match_sample_isotopes_df, id_keys=("target_isotope_id", "sample_item_id")
        )

    # Sort and paginate the DataFrame
    match_sample_isotopes_df = sort_and_paginate_match_sample_df(
        match_sample_isotopes_df, order, page, limit
    )

    return {
        "message": f"Successfully retrieved target isotopes match data for sample '{sample['sample_item_name']}'.",
        "results": len(match_sample_isotopes_df),
        "data": match_sample_isotopes_df.to_dict(orient="records"),
    }
