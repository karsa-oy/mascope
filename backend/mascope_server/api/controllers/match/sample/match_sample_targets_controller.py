from typing import Optional
import pandas as pd
import numpy as np
from mascope_server.api.utils.api_features import api_controller
from mascope_server.api.controllers.samples_controller import get_sample
from mascope_server.api.controllers.sample_items_controller import get_sample_item
from mascope_server.api.controllers.target_collections_controller import (
    get_target_collections,
)
from mascope_server.api.controllers.target_compounds_controller import (
    get_target_compounds,
)
from mascope_server.api.controllers.target_ions_controller import get_target_ions
from mascope_server.api.controllers.target_isotopes_controller import (
    get_target_isotopes,
)
from mascope_server.api.controllers.match.match_collections_controller import (
    get_match_collections,
)
from mascope_server.api.controllers.match.match_compounds_controller import (
    get_match_compounds,
)
from mascope_server.api.controllers.match.match_ions_controller import get_match_ions
from mascope_server.api.controllers.match.match_isotopes_controller import (
    get_match_isotopes,
)
from mascope_server.api.controllers.match.match_interferences_controller import (
    get_match_interferences,
)
from mascope_server.api.controllers.match.match_data_ops import apply_filter_params
import mascope_runtime as runtime

logger = runtime.logger.service("backend")


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
    sample = await get_sample_item(sample_item_id)
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
    match_data = {
        item["target_collection_id"]: item for item in match_collections["data"]
    }
    match_sample_collections = []
    for collection in target_collections["data"]:
        collection.update(
            match_data.get(
                collection["target_collection_id"],
                {
                    "match_collection_id": None,
                    "sample_item_id": sample_item_id,
                    "match_score": None,
                    "match_category": None,
                    "sample_peak_area_sum": None,
                    "sample_peak_interference_sum": None,
                    "match_collection_utc_created": None,
                    "match_collection_utc_modified": None,
                },
            )
        )
        match_sample_collections.append(collection)

    # Sorting and pagination logic
    match_sample_collections_sorted = sorted(
        match_sample_collections,
        key=lambda x: (
            x["target_collection_id"],
            x["match_category"],
            x["match_score"],
        ),
        reverse=(order == "desc"),
    )
    match_sample_collections_paginated = match_sample_collections_sorted[
        page * limit : (page + 1) * limit
    ]

    return {
        "results": len(match_sample_collections_sorted),
        "message": f"Successfully retrieved target collection matches for sample '{sample_item_name}'.",
        "data": match_sample_collections_paginated,
    }


@api_controller()
async def get_match_sample_compounds(
    sample_item_id: str,
    target_collection_id: Optional[str] = None,
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
    sample = await get_sample_item(sample_item_id)
    sample_batch_id = sample["sample_batch_id"]
    sample_item_name = sample["sample_item_name"]

    # Fetch target compounds with filters:
    #   - sample_batch_id - target_compounds for the sample batch (unique)
    #   - target_collection_id - target_compounds for particular target_collection (unique)
    #   - show_target_collection - add target collection id and adds potential compount duplicates
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
    match_data = {item["target_compound_id"]: item for item in match_compounds["data"]}
    match_sample_compounds = []
    for compound in target_compounds["data"]:
        compound.update(
            match_data.get(
                compound["target_compound_id"],
                {
                    "match_compound_id": None,
                    "sample_item_id": sample_item_id,
                    "match_score": None,
                    "match_category": None,
                    "sample_peak_area_sum": None,
                    "sample_peak_interference_sum": None,
                    "match_compound_utc_created": None,
                    "match_compound_utc_modified": None,
                },
            )
        )
        match_sample_compounds.append(compound)

    # Sorting and pagination logic
    match_sample_compounds_sorted = sorted(
        match_sample_compounds,
        key=lambda x: (
            x["target_collection_id"],
            x["match_category"],
            x["match_score"],
        ),
        reverse=(order == "desc"),
    )
    match_sample_compounds_paginated = match_sample_compounds_sorted[
        page * limit : (page + 1) * limit
    ]

    return {
        "results": len(match_sample_compounds_sorted),
        "message": f"Successfully retrieved target compound matches for sample '{sample_item_name}'.",
        "data": match_sample_compounds_paginated,
    }


@api_controller()
async def get_match_sample_ions(
    sample_item_id: str,
    target_compound_id: Optional[str] = None,
    target_collection_id: Optional[str] = None,
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
    sample = await get_sample_item(sample_item_id)
    sample_batch_id = sample["sample_batch_id"]
    sample_item_name = sample["sample_item_name"]

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
            "message": f"No target ions found for sample '{sample_item_name}'.",
            "data": [],
        }

    # Fetch match ions for the sample item with collection details
    match_ions = await get_match_ions(
        sample_item_id=sample_item_id,
    )

    # Merging: Combine target ions DataFrame with match ions DataFrame
    target_ions_df = pd.DataFrame(target_ions["data"])
    match_ions_df = pd.DataFrame(match_ions["data"]).set_index("target_ion_id")
    match_sample_ions_df = pd.merge(
        target_ions_df,
        match_ions_df,
        left_on="target_ion_id",
        right_index=True,
        how="left",
    )

    # Replace match_score and match_category NaN for sorting and ensure match_category remains integer
    match_sample_ions_df["match_score"] = match_sample_ions_df["match_score"].fillna(-1)
    match_sample_ions_df["match_category"] = (
        match_sample_ions_df["match_category"].fillna(-1).astype(int)
    )

    # Sorting data
    sort_ascending = [(order != "desc"), (order != "desc"), (order != "desc")]
    match_sample_ions_df = match_sample_ions_df.sort_values(
        by=["target_collection_id", "match_category", "match_score"],
        ascending=sort_ascending,
    )

    # Pagination logic
    match_sample_ions_df = match_sample_ions_df.iloc[page * limit : (page + 1) * limit]

    # Replace -1 back to None for match_category and match_score if it was originally NaN
    match_sample_ions_df["match_score"] = match_sample_ions_df["match_score"].replace(
        -1, None
    )
    match_sample_ions_df["match_category"] = match_sample_ions_df[
        "match_category"
    ].replace(-1, None)

    # Replace all other NaN and NaT with None for JSON compatibility
    match_sample_ions_df = match_sample_ions_df.replace([np.nan, pd.NaT], None)

    logger.debug(match_sample_ions_df)

    return {
        "results": len(match_sample_ions_df),
        "message": f"Successfully retrieved target ion matches for sample '{sample_item_name}'.",
        "data": match_sample_ions_df.to_dict(orient="records"),
    }


@api_controller()
async def get_match_sample_isotopes(
    sample_item_id: str,
    target_ion_id: Optional[str] = None,
    min_relative_abundance: Optional[str] = None,
    target_collection_id: Optional[str] = None,
    order: Optional[str] = "desc",
    page: int = 0,
    limit: int = 10000,
) -> dict:
    """
    Retrieves a list of sample target isotopes joined with match isotope and interference data for a given sample item ID,
    and allows sorting and pagination of the results. All data manipulation is handled within DataFrames and that NaNs
    and NaTs are replaced with None for JSON serialization.

    Steps:
    1. Retrieve the sample item data, including batch ID, sample name, and instrument.
    2. Fetch target isotopes based on the filter parameters including batch, ion, and collection IDs.
    3. If no target isotopes are found, return a response indicating no data.
    4. Fetch matched isotopes and interference data based on the sample item ID.
    5. Merge target isotope data with matched isotopes and interference data using DataFrames.
    6. Add sample instrument data to each merged record.
    7. Apply filtering parameters to adjust the match score and categorize matches.
    8. Sort the filtered DataFrame based on 'target_collection_id', 'match_category', and 'match_score', handling NaNs appropriately.
    9. Paginate the sorted data and prepare it for output by replacing placeholders for absent data with None.
    10. Return the paginated data along with success or informative messages.

    :param sample_item_id: Unique identifier of the sample item.
    :type sample_item_id: str
    :param target_ion_id: Filter isotopes by target ion ID, defaults to None.
    :type target_ion_id: Optional[str], optional
    :param min_relative_abundance: Filter isotopes by minimum relative abundance, defaults to None.
    :type min_relative_abundance: Optional[str], optional
    :param target_collection_id: Filter isotopes by target collection ID, defaults to None.
    :type target_collection_id: Optional[str], optional
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
    sample = await get_sample(sample_item_id)
    sample_batch_id = sample["sample_batch_id"]
    sample_item_name = sample["sample_item_name"]
    instrument = sample["instrument"]

    # Fetch target isotopes for the sample batch with filter parameters
    target_isotopes = await get_target_isotopes(
        target_ion_id=target_ion_id,
        min_relative_abundance=min_relative_abundance,
        sample_batch_id=sample_batch_id,
        target_collection_id=target_collection_id,
        show_target_collection=True,
        show_filter_params=True,
    )
    if not target_isotopes["data"]:
        return {
            "results": 0,
            "message": f"No target isotopes found for sample '{sample_item_name}'.",
            "data": [],
        }
    # Fetch match isotopes and interferences for the sample item
    match_isotopes = await get_match_isotopes(sample_item_id=sample_item_id)
    match_interferences = await get_match_interferences(sample_item_id=sample_item_id)

    # Create DataFrames
    target_df = pd.DataFrame(target_isotopes["data"])
    match_iso_df = pd.DataFrame(match_isotopes["data"]).set_index("target_isotope_id")
    interference_df = pd.DataFrame(match_interferences["data"]).set_index(
        "target_isotope_id"
    )

    # Merge DataFrames
    match_sample_isotopes_df = pd.merge(
        target_df,
        match_iso_df,
        left_on="target_isotope_id",
        right_index=True,
        how="left",
    ).merge(interference_df, left_on="target_isotope_id", right_index=True, how="left")

    # Add instrument data to each record for filtering logic
    match_sample_isotopes_df["instrument"] = instrument

    # Apply filtering to filter the match_score and assign match_category
    match_sample_isotopes_df = apply_filter_params(match_sample_isotopes_df)

    # Replace match_score and match_category NaN for sorting and ensure match_category remains integer
    match_sample_isotopes_df["match_score"] = match_sample_isotopes_df[
        "match_score"
    ].fillna(-1)
    match_sample_isotopes_df["match_category"] = (
        match_sample_isotopes_df["match_category"].fillna(-1).astype(int)
    )

    # Sorting data
    sort_ascending = [(order != "desc"), (order != "desc"), (order != "desc")]
    match_sample_isotopes_df = match_sample_isotopes_df.sort_values(
        by=["target_collection_id", "match_category", "match_score"],
        ascending=sort_ascending,
    )

    # Pagination logic
    match_sample_isotopes_df = match_sample_isotopes_df.iloc[
        page * limit : (page + 1) * limit
    ]

    # Replace -1 back to None for match_category and match_score if it was originally NaN
    match_sample_isotopes_df["match_score"] = match_sample_isotopes_df[
        "match_score"
    ].replace(-1, None)
    match_sample_isotopes_df["match_category"] = match_sample_isotopes_df[
        "match_category"
    ].replace(-1, None)

    # Replace all other NaN and NaT with None for JSON compatibility
    match_sample_isotopes_df = match_sample_isotopes_df.replace([np.nan, pd.NaT], None)

    logger.debug(match_sample_isotopes_df)

    return {
        "results": len(match_sample_isotopes_df),
        "message": f"Successfully retrieved target isotopes matches for sample '{sample['sample_item_name']}'.",
        "data": match_sample_isotopes_df.to_dict(orient="records"),
    }
