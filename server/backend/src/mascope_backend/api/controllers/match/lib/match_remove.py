"""
Match removal controller.

Provides consolidated orchestration entry point for determining which match data need removal
on all match levels by comparing current target isotope associations against existing match isotopes.
"""

from mascope_backend.db.models import Sample, SampleBatch
from mascope_backend.api.controllers.match.lib.match_fetch import (
    fetch_sample_orphaned_match_data,
    fetch_batch_orphaned_match_data,
)
from mascope_backend.api.lib.api_features import (
    api_controller,
)
from mascope_backend.api.controllers.match.isotopes.match_isotopes_controller import (
    delete_match_isotopes,
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
    sample: Sample | None = None,
    sample_batch: SampleBatch | None = None,
    full_remove: bool = False,
    match_isotopes: bool = True,
    match_ions: bool = True,
    match_compounds: bool = True,
    match_collections: bool = True,
    match_samples: bool = True,
) -> dict:
    """
    Removes match data associated with specified sample or a sample batch.

    Supports three removal scenarios:
    1. Full removal: Removes all matches for specified sample(s)
    2. Partial removal: Removes only orphaned matches based on current target associations
    3. Selective removal: Removes specific match levels based on flags

    By default, performs partial removal by comparing existing match isotopes and related matches
    against current sample-target isotopes associations and removing only orphaned matches.

    :param sample: Sample model object for single sample operations
    :type sample: Sample | None
    :param sample_batch: SampleBatch model object for batch operations
    :type sample_batch: SampleBatch | None
    :param full_remove: If True, removes all matches; if False, removes only orphaned matches
    :type full_remove: bool
    :param match_isotopes: Whether to remove match_isotopes level
    :type match_isotopes: bool
    :param match_ions: Whether to remove match_ions level
    :type match_ions: bool
    :param match_compounds: Whether to remove match_compounds level
    :type match_compounds: bool
    :param match_collections: Whether to remove match_collections level
    :type match_collections: bool
    :param match_samples: Whether to remove match_samples level
    :type match_samples: bool
    :raises ValueError: When invalid parameter combination provided
    :return: Dictionary with operation results and removal statistics
    :rtype: dict
    """
    # Validate input parameters
    if (not sample and not sample_batch) or (sample and sample_batch):
        raise ValueError("Either sample or sample_batch must be provided")

    sample_item_id = sample.sample_item_id if sample else None
    sample_batch_id = sample_batch.sample_batch_id if sample_batch else None
    entity_name = sample.sample_item_name if sample else sample_batch.sample_batch_name
    entity_type = "sample" if sample else "sample batch"

    # Get orphaned data for partial removal
    orphaned_match_data = None
    if not full_remove:
        orphaned_match_data = (
            await fetch_sample_orphaned_match_data(sample)
            if sample
            else await fetch_batch_orphaned_match_data(sample_batch)
        )

        if not orphaned_match_data.has_orphaned_data:
            runtime.logger.debug(
                f"No orphaned matches found for {entity_type} '{entity_name}'"
            )
            return {
                "status": "skipped",
                "message": f"No orphaned matches found for {entity_type} '{entity_name}'",
                "data": {"removed_match_isotopes_count": 0},
            }

    # Build operations list with conditional parameters
    operations = []

    if match_isotopes:
        params = (
            {"target_isotope_ids": orphaned_match_data.target_isotope_ids}
            if not full_remove
            else {}
        )
        operations.append((delete_match_isotopes, "match_isotopes", params))

    if match_ions:
        params = (
            {"target_ion_ids": orphaned_match_data.target_ion_ids}
            if not full_remove
            else {}
        )
        operations.append((delete_match_ions, "match_ions", params))

    if match_compounds:
        params = (
            {"target_compound_ids": orphaned_match_data.target_compound_ids}
            if not full_remove
            else {}
        )
        operations.append((delete_match_compounds, "match_compounds", params))

    if match_collections:
        params = (
            {"target_collections_ids": orphaned_match_data.target_collection_ids}
            if not full_remove
            else {}
        )
        operations.append((delete_match_collections, "match_collections", params))

    if match_samples:
        operations.append((delete_match_samples, "match_samples", {}))

    if not operations:
        raise ValueError(
            "No deletion operations specified - at least one match level must be enabled"
        )

    # Execute operations with concise parameter injection
    for delete_func, description, params in operations:
        if sample_batch_id:
            params["sample_batch_id"] = sample_batch_id
        if sample_item_id:
            params["sample_item_id"] = sample_item_id

        await delete_func(**params)

    # Generate result message
    operation_type = "Full" if full_remove else "Partial"
    removed_levels = [op[1].replace("match_", "") for op in operations]
    removed_description = (
        "all match levels"
        if len(removed_levels) == 5
        else f"match {', '.join(removed_levels)}"
    )

    message = f"{operation_type.title()} removal completed for {entity_type} '{entity_name}': removed {removed_description}"
    if not full_remove and orphaned_match_data:
        message += f" ({orphaned_match_data.isotopes_count} orphaned isotope matches)"

    runtime.logger.info(message)

    return {
        "status": "success",
        "message": message,
        "data": {
            "removed_match_isotopes_count": (
                orphaned_match_data.isotopes_count if orphaned_match_data else 0
            ),
            "operation_type": operation_type,
            "removed_levels": removed_levels,
        },
    }
