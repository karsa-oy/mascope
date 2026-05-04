"""
Target collection utility functions for target collection operations and change detection.

This module contains helper functions for target collection management operations,
including change detection, validation utilities, and data transformation
functions used across target collection-related controllers.
"""

from mascope_backend.api.models.target.collections.target_collection_pydantic_model import (
    TargetCollectionUpdate,
)
from mascope_backend.db import (
    TargetCollection,
)
from mascope_backend.runtime import runtime


def detect_target_collection_changes(
    target_collection_db: TargetCollection,
    target_collection_update: TargetCollectionUpdate,
    updated_compound_ids: set[str] | None = None,
) -> dict[str, bool | set[str]]:
    """
    Detects changes between existing target collection and update data.

    Compares current collection state with proposed updates to determine
    which fields have actually changed and what specific items need to be
    added or removed.

    :param target_collection_db: Current target collection entity from database
    :type target_collection_db: TargetCollection
    :param target_collection_update: Pydantic model containing proposed updates
    :type target_collection_update: TargetCollectionUpdate
    :param updated_compound_ids: Final compound IDs that should be associated with the
                                 collection
    :type updated_compound_ids: set[str] | None
    :return: Dictionary mapping change types to boolean flags and sets of IDs
    :rtype: dict[str, bool | set[str]]
    """
    sample_batches_db = {sb.sample_batch_id for sb in target_collection_db.sample_batch}
    target_compounds_db = {
        tc.target_compound_id for tc in target_collection_db.target_compound
    }
    # Calculate compound changes
    compounds_changed = False
    compounds_to_add = set()
    compounds_to_remove = set()
    if updated_compound_ids is not None:
        compounds_to_add = updated_compound_ids - target_compounds_db
        compounds_to_remove = target_compounds_db - updated_compound_ids
        compounds_changed = len(compounds_to_add) > 0 or len(compounds_to_remove) > 0

    # Calculate batch changes
    batches_changed = False
    batches_to_add = set()
    batches_to_remove = set()
    if target_collection_update.sample_batch_ids is not None:
        desired_batches = set(target_collection_update.sample_batch_ids)
        batches_to_add = desired_batches - sample_batches_db
        batches_to_remove = sample_batches_db - desired_batches
        batches_changed = len(batches_to_add) > 0 or len(batches_to_remove) > 0

    # Basic field changes
    collection_type_changed = (
        target_collection_update.target_collection_type is not None
        and target_collection_update.target_collection_type
        != target_collection_db.target_collection_type
    )
    name_changed = (
        target_collection_update.target_collection_name is not None
        and target_collection_update.target_collection_name
        != target_collection_db.target_collection_name
    )
    description_changed = (
        target_collection_update.target_collection_description is not None
        and target_collection_update.target_collection_description
        != target_collection_db.target_collection_description
    )
    basic_fields_changed = (
        collection_type_changed or name_changed or description_changed
    )

    runtime.logger.debug(
        "Detected target collection changes:\n"
        f"  basic_fields_changed: {basic_fields_changed}\n"
        f"  compounds_changed: {compounds_changed}\n"
        f"  compounds_to_add: {list(compounds_to_add)}\n"
        f"  compounds_to_remove: {list(compounds_to_remove)}\n"
        f"  batches_changed: {batches_changed}\n"
        f"  batches_to_add: {list(batches_to_add)}\n"
        f"  batches_to_remove: {list(batches_to_remove)}"
    )

    return {
        "compounds": compounds_changed,
        "compounds_to_add": compounds_to_add,
        "compounds_to_remove": compounds_to_remove,
        "batches": batches_changed,
        "batches_to_add": batches_to_add,
        "batches_to_remove": batches_to_remove,
        "basic_fields": basic_fields_changed,
        "collection_type": collection_type_changed,
    }
