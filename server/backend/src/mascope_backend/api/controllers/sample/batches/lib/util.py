"""
Sample batch utility functions for batch operations and change detection.

This module contains helper functions for sample batch management operations,
including change detection, validation utilities, and data transformation
functions used across batch-related controllers.
"""

from mascope_backend.runtime import runtime


def detect_update_batch_changes(existing_batch, sample_batch_update) -> dict[str, bool]:
    """
    Detects changes between existing sample batch and update data.

    Compares current batch state with proposed updates to determine which
    fields have actually changed. This enables efficient updates by only
    modifying changed fields and triggering appropriate reload events.

    :param existing_batch: Current sample batch entity from database
    :type existing_batch: SampleBatch
    :param sample_batch_update: Pydantic model containing proposed update values
    :type sample_batch_update: SampleBatchUpdate
    :return: Dictionary mapping change types to boolean flags
    :rtype: dict[str, bool]
    """
    # Extract current state for comparison
    current_ion_mechanisms = set(existing_batch.build_params["ion_mechanisms"])
    current_collections = {
        tc.target_collection_id for tc in existing_batch.target_collection
    }
    current_calibration = set(
        existing_batch.build_params.get("calibration_ion_mechanisms", [])
    )

    # Extract proposed new state using dot notation
    new_ion_mechanisms = set(sample_batch_update.build_params.ion_mechanisms)
    new_collections = set(sample_batch_update.target_collection_ids)
    new_calibration = set(sample_batch_update.build_params.calibration_ion_mechanisms)

    # Calculate collection changes
    collections_to_add = new_collections - current_collections
    collections_to_remove = current_collections - new_collections
    collections_changed = len(collections_to_add) > 0 or len(collections_to_remove) > 0

    # Basic field changes
    name_changed = (
        sample_batch_update.sample_batch_name is not None
        and existing_batch.sample_batch_name != sample_batch_update.sample_batch_name
    )
    description_changed = (
        sample_batch_update.sample_batch_description is not None
        and existing_batch.sample_batch_description
        != sample_batch_update.sample_batch_description
    )

    runtime.logger.debug(
        "Detected sample batch changes: "
        f"ion_mechanisms_changed: {current_ion_mechanisms != new_ion_mechanisms}, "
        f"calibration_changed: {current_calibration != new_calibration}, "
        f"collections_changed: {collections_changed}, "
        f"collections_to_add: {list(collections_to_add)}, "
        f"collections_to_remove: {list(collections_to_remove)}, "
        f"name_changed: {name_changed}, "
        f"description_changed: {description_changed}"
    )

    return {
        "ion_mechanisms": current_ion_mechanisms != new_ion_mechanisms,
        "calibration": current_calibration != new_calibration,
        "collections": collections_changed,
        "collections_to_add": collections_to_add,
        "collections_to_remove": collections_to_remove,
        "name": name_changed,
        "description": description_changed,
    }
