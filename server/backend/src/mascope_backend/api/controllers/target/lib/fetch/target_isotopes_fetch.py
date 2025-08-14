"""
Target isotope fetching utilities for match computation.

Provides data fetching operations for target isotopes, polarity filtering
capabilities, optimized for batch processing scenarios.
"""

import pandas as pd
from mascope_backend.api.controllers.sample.lib.sample_batches_fetch import (
    fetch_sample_batch_data,
)
from mascope_backend.api.controllers.target.lib.fetch.target_compounds_fetch import (
    fetch_sample_batch_compounds,
)
from mascope_backend.api.controllers.target.isotopes.target_isotopes_controller import (
    get_target_isotopes,
)

from mascope_backend.runtime import runtime


async def fetch_batch_target_isotopes_for_match_compute(
    sample_batch_id: str,
    added_target_compound_ids: list[str] | None = None,
    added_ionization_mechanism_ids: list[str] | None = None,
) -> pd.DataFrame:
    """
    Retrieves a DataFrame of target isotopes associated with a given sample batch.

    Optionally retrieves target isotope IDs that are associated with specific added compounds or
    ionization mechanisms and sample batch.
    Include ionization mechanism polarity data for further sample-level polarity filtering.
    This function helps in identifying the isotopes that require new match isotope lvl computation
    after the update in batch composition.

    Steps:
    1. Fetch the batch data, including ionization mechanisms and target compounds.
    2. Fetch isotopes related to added target compounds and ionization mechanisms, if provided.
    3. If no specific additions are made, fetch all isotopes associated with the sample batch.
    4. Combine and deduplicate the isotopes from the fetched data and return them in a DataFrame.

    :param sample_batch_id: The ID of the sample batch for which to fetch target isotopes.
    :type sample_batch_id: str
    :param added_target_compound_ids: Optional list of added target compound IDs for which to fetch related isotopes.
    :type added_target_compound_ids: Optional[List[str]], optional
    :param added_ionization_mechanism_ids: Optional list of added ionization mechanism IDs for which to fetch related isotopes.
    :type added_ionization_mechanism_ids: Optional[List[str]], optional
    :return: A DataFrame containing the relevant target isotopes for match computation.
    :rtype: pd.DataFrame
    """

    # Step 1: Retrieve batch data (ionization mechanisms and target compounds).
    sample_batch_data = await fetch_sample_batch_data(sample_batch_id)
    batch_target_compounds_ids = await fetch_sample_batch_compounds(sample_batch_id)

    target_isotopes = []
    applied_filters = []

    # Helper function to add unique isotopes
    def add_unique_isotopes(isotope_data, filter_type):
        for isotope in isotope_data:
            if isotope not in target_isotopes:
                target_isotopes.append(isotope)
        if isotope_data:
            applied_filters.append(
                f"{len(isotope_data)} target isotopes associated with {filter_type}"
            )

    # Step 2: Fetch isotopes related to added target compounds and ionization mechanisms
    if added_target_compound_ids or added_ionization_mechanism_ids:
        # Fetch isotopes related to added compounds
        if added_target_compound_ids:
            added_compounds_isotopes_result = await get_target_isotopes(
                target_compound_ids=added_target_compound_ids,
                ionization_mechanism_ids=sample_batch_data.ion_mechanisms,
                show_ionization_mechanism=True,
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
                show_ionization_mechanism=True,
            )
            add_unique_isotopes(
                added_ion_mechanism_isotopes_result["data"],
                f"{len(added_ionization_mechanism_ids)} added ionization mechanism{'s' if len(added_ionization_mechanism_ids) > 1 else ''}",
            )

        target_isotopes_df = pd.DataFrame(target_isotopes)
        runtime.logger.info(
            f"Match isotopes computing is specified for the list of { ", ".join(applied_filters)}"
        )
    # Step 3: Fetch all target isotopes if no specific additions
    else:
        target_isotopes_result = await get_target_isotopes(
            sample_batch_id=sample_batch_id,
            show_ionization_mechanism=True,
        )
        target_isotopes_df = pd.DataFrame(target_isotopes_result["data"])
        runtime.logger.info(
            f"Match isotopes computing for all associated target isotopes. Total isotopes: {len(target_isotopes_df)}"
        )

    return target_isotopes_df


def filter_target_isotopes_by_polarity(
    target_isotopes_df: pd.DataFrame, sample_polarity: str
) -> pd.DataFrame:
    """
    Filter target isotopes DataFrame by sample polarity.

    :param target_isotopes_df: DataFrame containing target isotopes with ionization mechanism polarity.
    :type target_isotopes_df: pd.DataFrame
    :param sample_polarity: The polarity of the sample ('+', '-').
    :type sample_polarity: str
    :return: Filtered DataFrame containing only polarity-compatible target isotopes.
    :rtype: pd.DataFrame
    """
    if (
        target_isotopes_df.empty
        or "ionization_mechanism_polarity" not in target_isotopes_df.columns
    ):
        runtime.logger.warning(
            f"Target isotopes DataFrame is empty or missing polarity data for sample polarity '{sample_polarity}'"
        )
        return pd.DataFrame()

    # Filter isotopes by ionization_mechanism and sample polarity
    polarity_filtered_df = (
        target_isotopes_df[
            target_isotopes_df["ionization_mechanism_polarity"] == sample_polarity
        ]
        .copy()
        .reset_index(drop=True)
    )

    runtime.logger.debug(
        f"Filtered batch target isotopes by ionization_mechanism_polarity matching sample_polarity '{sample_polarity}': "
        f"{len(polarity_filtered_df)}/{len(target_isotopes_df)} isotopes are compatible"
    )

    return polarity_filtered_df
