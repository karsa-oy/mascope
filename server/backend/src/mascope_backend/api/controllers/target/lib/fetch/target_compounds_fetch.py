from typing import List, Dict
from mascope_backend.api.controllers.target.compounds.target_compounds_controller import (
    get_target_compounds,
)

from mascope_backend.runtime import runtime


async def fetch_batches_compounds(
    sample_batches: List[str], show_duplicates: False
) -> Dict[str, List[str]]:
    """
    Retrieves the target compounds associated with a list of sample batch IDs. This function is intended to gather
    the current state of target compounds for each batch, either before or after updates to the target collection.

    :param sample_batches: List of sample batch IDs to fetch target compounds for.
    :type sample_batches: List[str]
    :return: A dictionary with sample batch IDs as keys and lists of target compound IDs as values.
    :rtype: Dict[str, List[str]]

    Usage:
    - This function is used in the `update_target_collection` process, both before and after applying updates to the target collection,
      to understand the changes in the association of target compounds with sample batches. It aids in determining the need for and scope of rematch operations.
    """
    batches_compounds_dict = {}

    for sample_batch_id in sample_batches:
        batch_compounds_result = await get_target_compounds(
            sample_batch_id=sample_batch_id, show_target_collection=show_duplicates
        )

        # Extract target compound IDs from the result and assign to the corresponding batch ID in the dictionary
        batches_compounds_dict[sample_batch_id] = [
            compound["target_compound_id"]
            for compound in batch_compounds_result["data"]
        ]

    return batches_compounds_dict


async def fetch_sample_batch_compounds(
    sample_batch_id: str, show_duplicates: bool = False
) -> List[str]:
    """
    Fetches the target compounds associated with a specific sample batch ID.

    :param sample_batch_id: The ID of the sample batch to fetch target compounds for.
    :type sample_batch_id: str
    :param show_duplicates: Flag indicating whether to show target collections with potential duplicates.
    :type show_duplicates: bool, optional
    :return: A list of target compound IDs associated with the sample batch.
    :rtype: List[str]
    :raises NotFoundException: If the sample batch has no associated target compounds.
    """
    # Fetch target compounds for the given sample batch ID
    batch_target_compounds_result = await get_target_compounds(
        sample_batch_id=sample_batch_id, show_target_collection=show_duplicates
    )

    # Extract target compound IDs from the result
    batch_target_compounds_ids = [
        compound["target_compound_id"]
        for compound in batch_target_compounds_result["data"]
    ]

    # Log the warning if no compounds are found
    if not batch_target_compounds_ids:
        runtime.logger.warning(
            f"No target compounds found for sample batch with ID '{sample_batch_id}'"
        )

    return batch_target_compounds_ids
