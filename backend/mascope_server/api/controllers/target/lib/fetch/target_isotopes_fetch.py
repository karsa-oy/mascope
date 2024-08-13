from typing import Optional, List, Tuple
from mascope_server.api.controllers.target.isotopes.target_isotopes_controller import (
    get_target_isotopes,
)

import mascope_runtime as runtime

logger = runtime.logger.service("backend")


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
