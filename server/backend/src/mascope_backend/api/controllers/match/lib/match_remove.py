from typing import List, Optional
from mascope_backend.api.lib.api_features import (
    api_controller,
)

from mascope_backend.api.controllers.target.lib.fetch.target_fetch import (
    fetch_targets_for_match_remove,
)
from mascope_backend.api.controllers.match.isotopes.match_isotopes_controller import (
    delete_match_isotopes,
)
from mascope_backend.api.controllers.match.interferences.match_interferences_controller import (
    delete_match_interferences,
)
from mascope_backend.api.controllers.match.ions.match_ions_controller import (
    delete_match_ions,
)
from mascope_backend.api.controllers.match.compounds.match_compounds_controller import (
    delete_match_compounds,
)
from mascope_backend.api.controllers.match.collections.match_collections_controller import (
    delete_match_collections,
)
from mascope_backend.api.controllers.match.samples.match_samples_controller import (
    delete_match_samples,
)

from mascope_backend.runtime import runtime


@api_controller()
async def remove_matches(
    sample_item_id: Optional[str] = None,
    sample_batch_id: Optional[str] = None,
    removed_target_compound_ids: Optional[List[str]] = None,
    removed_ionization_mechanism_ids: Optional[List[str]] = None,
    match_interferences: Optional[bool] = True,
    match_isotopes: Optional[bool] = True,
    match_ions: Optional[bool] = True,
    match_compounds: Optional[bool] = True,
    match_collections: Optional[bool] = True,
    match_samples: Optional[bool] = True,
) -> dict:
    """
    Removes all match data associated with specified sample items or a sample batch.
    This operation can target a specific sample item or all items within a specified batch.

    Steps:
    1. Fetch sample item IDs using the utility function.
    2. Execute deletion operations for all match data types using the resolved sample item IDs.
    3. Compile messages from each deletion operation and report back.

    :param sample_item_id: ID of the single sample item for which matches are to be removed, optional.
    :param sample_batch_id: ID of the sample batch from which sample items are derived for deletion, optional.
    :return: A dictionary with a message and log of actions taken.
    """
    # Step 1: Determine the target IDs that are associated with the removed compounds or ionization mechanisms.
    targets = {
        "target_isotope_ids": [],
        "target_ion_ids": [],
        # "target_compound_ids": [],
    }
    filtered_targets_message = ""
    if removed_target_compound_ids or removed_ionization_mechanism_ids:
        targets = await fetch_targets_for_match_remove(
            removed_target_compound_ids, removed_ionization_mechanism_ids
        )
        filtered_targets_message = "Associated with:"
        if removed_target_compound_ids:
            filtered_targets_message += (
                f" {len(removed_target_compound_ids)} removed compound(s)."
            )
        if removed_ionization_mechanism_ids:
            filtered_targets_message += f" {len(removed_ionization_mechanism_ids)} removed ionization mechanism(s)."
    # Step 2: Delete matches corresponding to these targets.
    # List of operations including function references, description, and a dictionary of parameters
    delete_operations = []
    descriptions = []
    if match_interferences:
        delete_operations.append(
            (
                delete_match_interferences,
                "match_interferences",
                {"target_isotope_ids": targets["target_isotope_ids"]},
            )
        )
        descriptions.append("match_interferences")
    if match_isotopes:
        delete_operations.append(
            (
                delete_match_isotopes,
                "match_isotopes",
                {"target_isotope_ids": targets["target_isotope_ids"]},
            )
        )
        descriptions.append("match_isotopes")
    if match_ions:
        delete_operations.append(
            (
                delete_match_ions,
                "match_ions",
                {"target_ion_ids": targets["target_ion_ids"]},
            )
        )
        descriptions.append("match_ions")
    if match_compounds:
        delete_operations.append(
            (
                delete_match_compounds,
                "match_compounds",
                {},
            )
        )
        descriptions.append("match_compounds")
    if match_collections:
        delete_operations.append((delete_match_collections, "match_collections", {}))
        descriptions.append("match_collections")
    if match_samples:
        delete_operations.append((delete_match_samples, "match_samples", {}))
        descriptions.append("match_samples")

    delete_matches_message = (
        "all matches" if len(descriptions) == 6 else ", ".join(descriptions)
    )
    runtime.logger.info(
        f"Removing {delete_matches_message}. {filtered_targets_message}"
    )

    message_logs = []
    for delete_func, description, params in delete_operations:
        # Injecting common sample id parameter
        if sample_batch_id:
            params["sample_batch_id"] = sample_batch_id
        if sample_item_id:
            params["sample_item_id"] = sample_item_id
        result = await delete_func(**params)
        message_logs.append(f"{description}: {result['message']}")

    message = (
        f"Removed successfully {delete_matches_message}. {filtered_targets_message}"
    )
    return {
        "message": message,
        "message_logs": message_logs,
    }
