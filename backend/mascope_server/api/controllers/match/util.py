from typing import Optional, List, Tuple, Dict
import pandas as pd
import numpy as np
from sqlalchemy import select
from mascope_server.db import async_session
from mascope_server.api.exceptions import NotFoundException
from mascope_server.api.controllers.target_isotopes_controller import (
    get_target_isotopes,
)
from mascope_server.api.models.models import (
    SampleItem,
    SampleBatch,
    TargetIon,
)

import mascope_runtime as runtime

logger = runtime.logger.service("backend")


# -------------------------------------------------------------------
# Utility Functions
# -------------------------------------------------------------------


async def fetch_sample_item_ids(
    sample_item_id: Optional[str] = None, sample_batch_id: Optional[str] = None
) -> Tuple[List[str], str]:
    """
    Fetches sample item IDs and reference details based on provided sample_item_id or sample_batch_id.

    :param sample_item_id: Optional single sample item ID.
    :param sample_batch_id: Optional sample batch ID from which to derive sample item IDs.
    :return: A tuple containing a list of sample item IDs and a reference string for logging.
    :raises ValueError: If neither sample_item_id nor sample_batch_id is provided.
    :raises NotFoundException: If no sample items are found for the provided batch ID.
    """
    if not sample_item_id and not sample_batch_id:
        raise ValueError("Please provide either a sample item ID or a sample batch ID.")

    sample_item_ids = []
    sample_ref = ""
    async with async_session() as session:
        if sample_item_id:
            sample_item = await session.get(SampleItem, sample_item_id)
            if not sample_item:
                logger.warning(f"No sample item found with ID '{sample_item_id}'.")
            sample_item_ids.append(sample_item_id)
            sample_ref = f"sample '{sample_item.sample_item_name}'"
        elif sample_batch_id:
            results = await session.execute(
                select(SampleItem).where(SampleItem.sample_batch_id == sample_batch_id)
            )
            sample_items = results.scalars().all()
            if not sample_items:
                error_msg = (
                    f"No sample items found for sample batch ID '{sample_batch_id}'."
                )
                logger.warning(error_msg)
            sample_item_ids = [item.sample_item_id for item in sample_items]
            batch = await session.get(SampleBatch, sample_batch_id)
            sample_ref = (
                f"sample batch '{batch.sample_batch_name}'"
                if batch
                else f"sample batch with ID '{sample_batch_id}'"
            )

    return sample_item_ids, sample_ref


async def fetch_target_isotopes_for_match_compute(
    batch_target_compounds_ids: List[str],
    batch_ion_mechanisms_ids: List[str],
    added_target_compound_ids: Optional[List[str]],
    added_ionization_mechanism_ids: Optional[List[str]],
) -> Tuple[List[dict], str]:
    """
    Retrieves a list of unique target isotope IDs that are associated with specific added compounds or
    ionization mechanisms and sample batch target compounds. Adds a description of applied filters.
    This function helps in identifying the isotopes that require new matches computation after the update in batch composition.

    Steps:
    1. Fetch isotopes related to added target compounds.
    2. Fetch isotopes related to added ionization mechanisms.
    3. Combine and deduplicate the isotope IDs from both sources.
    4. Create a description of applied filters based on the retrieved data.

    :param batch_target_compounds_ids: List of target compound IDs already associated with the batch.
    :type batch_target_compounds_ids: List[str]
    :param batch_ion_mechanisms_ids: List of ionization mechanism IDs already associated with the batch.
    :type batch_ion_mechanisms_ids: List[str]
    :param added_target_compound_ids: Optional list of added target compound IDs.
    :type added_target_compound_ids: Optional[List[str]]
    :param added_ionization_mechanism_ids: Optional list of added ionization mechanism IDs.
    :type added_ionization_mechanism_ids: Optional[List[str]]
    :return: A tuple containing a list of unique target isotope IDs and a string describing the applied filters.
    :rtype: Tuple[List[dict], str]
    """
    target_isotopes = []
    applied_filters = []

    # Function to add unique isotopes
    def add_unique_isotopes(isotope_data, filter_type):
        for isotope in isotope_data:
            if isotope not in target_isotopes:
                target_isotopes.append(isotope)
        if isotope_data:
            applied_filters.append(
                f"{len(isotope_data)} target isotopes associated with {filter_type}"
            )

    # Fetch isotopes related to added compounds
    if added_target_compound_ids:
        added_compounds_isotopes_result = await get_target_isotopes(
            target_compound_ids=added_target_compound_ids,
            ionization_mechanism_ids=batch_ion_mechanisms_ids,
        )
        add_unique_isotopes(
            added_compounds_isotopes_result["data"],
            f"{len(added_target_compound_ids)} added compound{'s' if len(added_target_compound_ids) > 1 else ''}",
        )

    # Fetch isotopes related to added ionization mechanisms
    if added_ionization_mechanism_ids:
        all_target_compound_ids = set(batch_target_compounds_ids).union(
            set(added_target_compound_ids or [])
        )
        added_ion_mechanism_isotopes_result = await get_target_isotopes(
            target_compound_ids=list(all_target_compound_ids),
            ionization_mechanism_ids=added_ionization_mechanism_ids,
        )
        add_unique_isotopes(
            added_ion_mechanism_isotopes_result["data"],
            f"{len(added_ionization_mechanism_ids)} added ionization mechanism{'s' if len(added_ionization_mechanism_ids) > 1 else ''}",
        )

    filters_description = ", ".join(applied_filters)
    return target_isotopes, filters_description


# async def fetch_targets_for_match_compute(
#     batch_target_compound_ids: List[str],
#     batch_ion_mechanisms_ids: List[str],
#     added_target_compound_ids: Optional[List[str]],
#     added_ionization_mechanism_ids: Optional[List[str]],
# ) -> Dict[str, List[str]]:
#     """
#     Retrieves target IDs for isotopes, ions, and compounds to be used in match computations following updates to a sample batch composition.

#     :param batch_target_compound_ids: List of target compound IDs already associated with the batch.
#     :param batch_ion_mechanisms_ids: List of ionization mechanism IDs already associated with the batch.
#     :param added_target_compound_ids: Optional list of newly added target compound IDs.
#     :param added_ionization_mechanism_ids: Optional list of newly added ionization mechanism IDs.
#     :return: A dictionary containing lists of unique target IDs for isotopes, ions, and compounds.
#     """
#     targets = {
#         "target_isotope_ids": [],
#         "target_ion_ids": [],
#         "target_compound_ids": [],
#     }

#     # Fetch isotopes and ions related to added compounds and existin batch ion mechanisms
#     if added_target_compound_ids:
#         added_compounds_isotopes_result = await get_target_isotopes(
#             target_compound_ids=added_target_compound_ids,
#             ionization_mechanism_ids=batch_ion_mechanisms_ids,
#         )
#         added_compounds_ions_result = await get_target_ions(
#             target_compound_ids=added_target_compound_ids,
#             ionization_mechanism_ids=batch_ion_mechanisms_ids,
#         )
#         targets["target_isotope_ids"].extend(
#             [
#                 target_isotope["target_isotope_id"]
#                 for target_isotope in added_compounds_isotopes_result["data"]
#             ]
#         )
#         targets["target_ion_ids"].extend(
#             [
#                 target_ion["target_ion_id"]
#                 for target_ion in added_compounds_ions_result["data"]
#             ]
#         )
#         # Set target_compound_ids only if there are no added ionization mechanisms
#         if not added_ionization_mechanism_ids:
#             targets["target_compound_ids"].extend(added_target_compound_ids)

#     if added_ionization_mechanism_ids:
#         all_target_compound_ids = set(batch_target_compound_ids).union(
#             set(added_target_compound_ids or [])
#         )
#         added_ion_mechanism_isotopes_result = await get_target_isotopes(
#             target_compound_ids=list(all_target_compound_ids),
#             ionization_mechanism_ids=added_ionization_mechanism_ids,
#         )
#         added_ion_mechanism_ions_result = await get_target_ions(
#             target_compound_ids=list(all_target_compound_ids),
#             ionization_mechanism_ids=added_ionization_mechanism_ids,
#         )
#         targets["target_isotope_ids"].extend(
#             [
#                 item["target_isotope_id"]
#                 for item in added_ion_mechanism_isotopes_result["data"]
#             ]
#         )
#         targets["target_ion_ids"].extend(
#             [item["target_ion_id"] for item in added_ion_mechanism_ions_result["data"]]
#         )

#     # Deduplicate the lists
#     for key in targets:
#         targets[key] = list(set(targets[key]))

#     return targets


async def fetch_targets_for_match_remove(
    removed_target_compound_ids: Optional[List[str]] = None,
    removed_ionization_mechanism_ids: Optional[List[str]] = None,
) -> Dict[str, List[str]]:
    """
    Retrieves lists of unique target IDs (isotopes, ions, and compounds) associated with specific removed compounds
    or ionization mechanisms. This aids in identifying the targets that should no longer have matches associated with them
    after updates in composition.

    :param removed_target_compound_ids: Optional list of removed target compound IDs.
    :type removed_target_compound_ids: Optional[List[str]]
    :param removed_ionization_mechanism_ids: Optional list of removed ionization mechanism IDs.
    :type removed_ionization_mechanism_ids: Optional[List[str]]
    :return: A dictionary containing lists of unique target IDs for isotopes, ions, and potentially compounds.
    :rtype: Dict[str, List[str]]
    TODO_api_circular_import reorginize the cross dependency for rematch and get_target_ controllers
    """
    targets = {
        "target_isotope_ids": [],
        "target_ion_ids": [],
        # "target_compound_ids": [],
    }

    # Fetch isotopes and ions related to removed compounds and mechanisms
    if removed_target_compound_ids:
        isotopes_result = await get_target_isotopes(
            target_compound_ids=removed_target_compound_ids
        )
        targets["target_isotope_ids"].extend(
            [item["target_isotope_id"] for item in isotopes_result["data"]]
        )
        # ions_result = await get_target_ions(
        #     target_compound_ids=removed_target_compound_ids
        # )
        # targets["target_ion_ids"].extend(
        #     [item["target_ion_id"] for item in ions_result["data"]]
        # )
        async with async_session() as session:
            ion_query = select(TargetIon).filter(
                TargetIon.target_compound_id.in_(removed_target_compound_ids)
            )
            ion_result = await session.execute(ion_query)
        ion_ids = [ion.target_ion_id for ion in ion_result.scalars().all()]
        targets["target_ion_ids"].extend(ion_ids)

        # # Set target_compound_ids only if there are no removed ionization mechanisms
        # if not removed_ionization_mechanism_ids:
        #     targets["target_compound_ids"].extend(removed_target_compound_ids)

    if removed_ionization_mechanism_ids:
        isotopes_result = await get_target_isotopes(
            ionization_mechanism_ids=removed_ionization_mechanism_ids
        )
        targets["target_isotope_ids"].extend(
            [item["target_isotope_id"] for item in isotopes_result["data"]]
        )
        # ions_result = await get_target_ions(
        #     ionization_mechanism_ids=removed_ionization_mechanism_ids
        # )
        # targets["target_ion_ids"].extend(
        #     [item["target_ion_id"] for item in ions_result["data"]]
        # )
        async with async_session() as session:
            ion_query = select(TargetIon).filter(
                TargetIon.ionization_mechanism_id.in_(removed_ionization_mechanism_ids)
            )
            ion_result = await session.execute(ion_query)
        ion_ids = [ion.target_ion_id for ion in ion_result.scalars().all()]
        targets["target_ion_ids"].extend(ion_ids)

    # Deduplicate the lists
    for key in targets:
        targets[key] = list(set(targets[key]))

    return targets


def sort_and_paginate_match_sample_df(
    df: pd.DataFrame, order: str, page: int, limit: int
) -> pd.DataFrame:
    """
    Sorts and paginates the DataFrame for match sample data. Used in endpoints match_sample_targets_controller
    Handles NaN values by treating them as -1 for sorting purposes and ensures JSON compatibility.

    Steps:
    1. Replace NaN values in 'match_score' and 'match_category' with -1 for sorting purposes.
    2. Convert 'match_category' to integer type.
    3. Sort the DataFrame by 'target_collection_id', 'match_category', and 'match_score'.
    4. Paginate the sorted DataFrame based on the 'page' and 'limit' parameters.
    5. Replace -1 back to None for 'match_score' and 'match_category'.
    6. Replace all other NaN and NaT values with None for JSON compatibility.

    :param df: DataFrame containing the match sample data to be sorted and paginated.
    :type df: pd.DataFrame
    :param order: Sorting order ('asc' or 'desc').
    :type order: str
    :param page: Page number for pagination.
    :type page: int
    :param limit: Number of items per page.
    :type limit: int
    :return: Sorted and paginated DataFrame with JSON compatible values.
    :rtype: pd.DataFrame
    """
    # Replace match_score and match_category NaN for sorting and ensure match_category remains integer
    # The option_context is used to avoid FutureWarning in pandas 3, where silent downcasting is deprecated.
    with pd.option_context("future.no_silent_downcasting", True):
        df["match_score"] = df["match_score"].fillna(-1)
        df["match_category"] = df["match_category"].fillna(-1).astype(int)

    # Sorting data
    sort_ascending = [(order != "desc"), (order != "desc"), (order != "desc")]
    df = df.sort_values(
        by=["target_collection_id", "match_category", "match_score"],
        ascending=sort_ascending,
    )

    # Pagination logic
    df = df.iloc[page * limit : (page + 1) * limit]

    # Replace -1 back to None for match_category and match_score if it was originally NaN
    df["match_score"] = df["match_score"].replace(-1, None)
    df["match_category"] = df["match_category"].replace(-1, None)

    # Replace all other NaN and NaT with None for JSON compatibility
    df = df.replace([np.nan, pd.NaT], None)

    return df
