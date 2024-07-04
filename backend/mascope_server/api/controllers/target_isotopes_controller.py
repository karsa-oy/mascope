from sqlalchemy import select, asc, desc, func
from sqlalchemy.orm import joinedload
from typing import List, Optional
from mascope_server.db import async_session
from ..utils.api_features import api_controller
from ..exceptions import NotFoundException
from ..models.models import (
    SampleBatch,
    TargetCollection,
    TargetCompoundInTargetCollection,
    TargetIon,
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
                raise NotFoundException(
                    f"Sample batch with id {sample_batch_id} not found"
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
        count_stmt = select(func.count()).select_from(  # pylint: disable=not-callable
            stmt
        )
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
