from typing import Optional, List, Dict, Tuple
from sqlalchemy import select
from mascope_backend.db import async_session
from mascope_backend.db.models import (
    TargetIon,
    TargetCompoundInTargetCollection,
    TargetCollectionInSampleBatch,
)
from mascope_backend.api.controllers.target.isotopes.target_isotopes_controller import (
    get_target_isotopes,
)

from mascope_backend.runtime import runtime


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


async def fetch_compound_collections_and_batches(
    target_compound_id: str,
) -> Tuple[str, str]:
    """
    Retrieves the associated target collection IDs and sample batch IDs for a given target compound ID.

    This function is used to fetch the collections that a target compound belongs to and the sample batches
    associated with those collections.

    :param target_compound_id: The ID of the target compound.
    :type target_compound_id: str
    :return: A tuple containing two sets - sample_batches_ids and target_collections_ids.
    :rtype: tuple(set, set)
    """
    async with async_session() as session:
        # Get the target collections for this compound
        target_collections = await session.execute(
            select(TargetCompoundInTargetCollection.target_collection_id).where(
                TargetCompoundInTargetCollection.target_compound_id
                == target_compound_id
            )
        )
        target_collections_ids = {tc[0] for tc in target_collections}

        # Get all affected sample batches
        sample_batches = await session.execute(
            select(TargetCollectionInSampleBatch.sample_batch_id).where(
                TargetCollectionInSampleBatch.target_collection_id.in_(
                    target_collections_ids
                )
            )
        )
        sample_batches_ids = {sb[0] for sb in sample_batches}

        return sample_batches_ids, target_collections_ids
