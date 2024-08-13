from typing import List, Tuple, Dict
from mascope_server.api.models.match.match_pydantic_model import (
    RematchBatchBody,
)


async def compare_batches_compounds(
    batches_compounds_before: Dict[str, List[str]],
    batches_compounds_after: Dict[str, List[str]],
) -> Tuple[List[RematchBatchBody], List[str]]:
    """
    Compares the target compounds associated with sample batches before and after updates to identify changes.
    This function is used for determining which compounds have been added or removed from each batch as a result of updates to the target collection assosiations.


    :param batches_compounds_before: The state of target compounds associated with sample batches before the updates.
    :type batches_compounds_before: Dict[str, List[str]]
    :param batches_compounds_after: The state of target compounds associated with sample batches after the updates.
    :type batches_compounds_after: Dict[str, List[str]]
    :return: A list of `RematchBatchBody` objects, each representing a sample batch that requires a rematch operation. Each object includes the batch ID and lists of added or removed target compound IDs.
    :rtype: List[RematchBatchBody]

    Usage:
    - In the `update_target_collection` function, after applying updates, this function is used to identify the exact changes in target compound associations for each sample batch.
      The resulting list of `RematchBatchBody` objects is used to construct `RematchBatchesBody` for the background rematch task, ensuring that the rematch operation only affects the necessary target compounds.

    """
    batches_rematch_data = []
    batches_to_reaggregate = []

    # Combine keys from both dictionaries to ensure all batches are considered
    all_batch_ids = set(batches_compounds_before.keys()) | set(
        batches_compounds_after.keys()
    )

    for batch_id in all_batch_ids:
        # Get compounds before and after update, defaulting to empty list if not present
        compounds_before = set(batches_compounds_before.get(batch_id, []))
        compounds_after = set(batches_compounds_after.get(batch_id, []))

        # Determine added and removed compounds
        added_compounds = compounds_after - compounds_before
        removed_compounds = compounds_before - compounds_after

        # Create RematchBatchBody only if there are changes
        if added_compounds or removed_compounds:
            rematch_batch = RematchBatchBody(
                sample_batch_id=batch_id,
                added_target_compound_ids=list(added_compounds),
                removed_target_compound_ids=list(removed_compounds),
            )
            batches_rematch_data.append(rematch_batch)

        # Compare compounds (including duplicates) before and after
        # to determine if a top lvl match reaggregation is needed
        if sorted(batches_compounds_before.get(batch_id, [])) != sorted(
            batches_compounds_after.get(batch_id, [])
        ):
            # Check for changes in the list itself, not just set comparisons
            if batch_id not in [
                batch.sample_batch_id for batch in batches_rematch_data
            ]:
                batches_to_reaggregate.append(batch_id)

    return batches_rematch_data, batches_to_reaggregate
