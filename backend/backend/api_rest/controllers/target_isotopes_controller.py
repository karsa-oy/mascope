from fastapi import HTTPException
from sqlalchemy import select, asc, desc, func
from sqlalchemy.orm import joinedload
from typing import List, Optional, Tuple
from backend.db_api_rest import async_session
from ..utils.api_features import api_controller
from ..exceptions import NotFoundException
from ..models.models import (
    Workspace,
    SampleBatch,
    SampleItem,
    TargetCollectionInSampleBatch,
    TargetCollection,
    TargetCompoundInTargetCollection,
    TargetCompound,
    TargetIon,
    IonizationMechanism,
    TargetIsotope,
)


@api_controller()
async def get_target_isotopes(
    target_ion_id: Optional[str] = None,
    min_mz: Optional[float] = None,
    max_mz: Optional[float] = None,
    min_relative_abundance: Optional[float] = None,
    max_relative_abundance: Optional[float] = None,
    target_compound_ids: Optional[List[str]] = None,
    ionization_mechanism_ids: Optional[List[str]] = None,
    sample_batch_id: Optional[str] = None,
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 1000000,
):
    """
    Retrieves a list of target isotopes based on various filters including target ion ID, mz range,
    relative abundance range, target compounds, and ionization mechanisms.

    :param target_ion_id: Target ion ID filter.
    :param min_mz: Minimum m/z filter.
    :param max_mz: Maximum m/z filter.
    :param min_relative_abundance: Minimum relative abundance filter.
    :param max_relative_abundance: Maximum relative abundance filter.
    :param target_compound_ids: List of target compound IDs for filtering.
    :param ionization_mechanism_ids: List of ionization mechanism IDs for filtering.
    :param sample_batch_id: ID of the sample batch for filtering.
    :param sort: Sorting field.
    :param order: Sorting order ('asc' or 'desc').
    :param page: Pagination page.
    :param limit: Number of items per page.
    :return: Dict with total count and list of target isotopes.
    """
    async with async_session() as session:
        stmt = select(TargetIsotope).join(
            TargetIon, TargetIon.target_ion_id == TargetIsotope.target_ion_id
        )

        # Apply filters
        if target_ion_id:
            stmt = stmt.filter(TargetIsotope.target_ion_id == target_ion_id)
        if min_mz is not None:
            stmt = stmt.filter(TargetIsotope.mz >= min_mz)
        if max_mz is not None:
            stmt = stmt.filter(TargetIsotope.mz <= max_mz)
        if min_relative_abundance is not None:
            stmt = stmt.filter(
                TargetIsotope.relative_abundance >= min_relative_abundance
            )
        if max_relative_abundance is not None:
            stmt = stmt.filter(
                TargetIsotope.relative_abundance <= max_relative_abundance
            )
        if target_compound_ids:
            stmt = stmt.where(TargetIon.target_compound_id.in_(target_compound_ids))

        if ionization_mechanism_ids:
            stmt = stmt.where(
                TargetIon.ionization_mechanism_id.in_(ionization_mechanism_ids)
            )

        if sample_batch_id:
            # Step 1: Fetch sample batch and related ion mechanisms and target collection ids
            result = await session.execute(
                select(SampleBatch)
                .options(joinedload(SampleBatch.target_collection))
                .where(SampleBatch.sample_batch_id == sample_batch_id)
            )
            sample_batch = result.unique().scalar_one_or_none()
            if not sample_batch:
                raise HTTPException(
                    status_code=404,
                    detail=f"Sample batch with id {sample_batch_id} not found",
                )

            # Extract ion mechanisms directly
            ionization_mechanism_ids = sample_batch.build_params["ion_mechanisms"]

            # Since we have eager loaded the target_collection, we can fetch them directly from sample_batch
            target_collection_ids = [
                tc.target_collection_id for tc in sample_batch.target_collection
            ]

            # Modify the statement to include filters based on target collections and ionization mechanisms
            stmt = (
                stmt.join(
                    TargetCompoundInTargetCollection,
                    TargetCompoundInTargetCollection.target_compound_id
                    == TargetIon.target_compound_id,
                )
                .join(
                    TargetCollection,
                    TargetCollection.target_collection_id
                    == TargetCompoundInTargetCollection.target_collection_id,
                )
                .where(
                    TargetCollection.target_collection_id.in_(target_collection_ids),
                    TargetIon.ionization_mechanism_id.in_(ionization_mechanism_ids),
                )
                .distinct()
            )

        # Apply sorting and pagination
        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(TargetIsotope, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(TargetIsotope, sort)))
        stmt = stmt.offset(page * limit).limit(limit)

        # Execute query
        result = await session.execute(stmt)
        target_isotopes = result.scalars().all()

        # Get total count
        count_stmt = select(func.count()).select_from(stmt)
        total = await session.scalar(count_stmt)

        return {
            "results": total,
            "data": [target_isotope.to_dict() for target_isotope in target_isotopes],
        }


@api_controller()
async def get_target_isotope(target_isotope_id: str) -> dict:
    """
    Retrieves a single target isotope by its unique ID.

    Steps:
    1. Execute a query to fetch the target isotope with the specified ID.
    2. Check if the target isotope exists. If not, raise a NotFoundException.
    3. Return the target isotope's details as a dictionary.

    :param sample_batch_id: Unique identifier of the target isotope to retrieve.
    :type sample_batch_id: str
    :raises NotFoundException: If the target isotope with the given ID is not found.
    :return: The requested target isotope's details.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Fetch target isotope by ID
        target_isotope = await session.get(TargetIsotope, target_isotope_id)

        if not target_isotope:
            # Step 2: If target isotope not found, raise exception
            raise NotFoundException(
                f"Target isotope with ID '{target_isotope_id}' not found"
            )
    # Step 3: Return target isotope details
    return target_isotope.to_dict()


async def get_target_isotopes_for_match_compute(
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


async def get_target_isotopes_for_match_remove(
    removed_target_compound_ids: Optional[List[str]],
    removed_ionization_mechanism_ids: Optional[List[str]],
) -> Tuple[List[str], str]:
    """

    Retrieves a list of unique target isotope IDs that are associated with specific added compounds or
    ionization mechanisms. Get ALL the assosiated isotopes, not filtering by sample_batch_id.
    This function aids in identifying the isotopes that should no longer have matches associated with them
    after the update in the batch composition. Adds a description of applied filters.

    Steps:
    1. Fetch isotopes related to removed target compounds.
    2. Fetch isotopes related to removed ionization mechanisms.
    3. Combine and deduplicate the isotope IDs from both sources.
    4. Create a description of applied filters based on the retrieved data.

    :param removed_target_compound_ids: Optional list of removed target compound IDs.
    :type removed_target_compound_ids: Optional[List[str]]
    :param removed_ionization_mechanism_ids: Optional list of removed ionization mechanism IDs.
    :type removed_ionization_mechanism_ids: Optional[List[str]]
    :return: A tuple containing a list of unique target isotope IDs and a string describing the applied filters.
    :rtype: Tuple[List[str], str]
    """
    unique_target_isotopes_ids = set()
    applied_filters = []

    # Function to add unique isotopes
    def add_unique_isotopes(isotope_data):
        for isotope in isotope_data:
            unique_target_isotopes_ids.add(isotope["target_isotope_id"])

    # Fetch isotopes related to removed compounds
    if removed_target_compound_ids:
        removed_compounds_isotopes_result = await get_target_isotopes(
            target_compound_ids=removed_target_compound_ids,
        )
        add_unique_isotopes(removed_compounds_isotopes_result["data"])
        applied_filters.append(
            f"{len(removed_target_compound_ids)} removed compound{'s' if len(removed_target_compound_ids) > 1 else ''}"
        )

    # Fetch isotopes related to removed ionization mechanisms
    if removed_ionization_mechanism_ids:
        removed_ion_mechanisms_isotopes_result = await get_target_isotopes(
            ionization_mechanism_ids=removed_ionization_mechanism_ids,
        )
        add_unique_isotopes(removed_ion_mechanisms_isotopes_result["data"])
        applied_filters.append(
            f"{len(removed_ionization_mechanism_ids)} removed ionization mechanism{'s' if len(removed_ionization_mechanism_ids) > 1 else ''}"
        )

    filters_description = ", ".join(applied_filters)
    return list(unique_target_isotopes_ids), filters_description
