from typing import List, Optional
from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import joinedload
from mascope_backend.db import async_session
from mascope_backend.db.models import (
    IonizationMechanism,
    TargetIon,
    TargetCompound,
    TargetCollection,
    TargetCompoundInTargetCollection,
    TargetCollectionInSampleBatch,
    SampleBatch,
    Sample,
)
from mascope_backend.api.lib.api_features import api_controller
from mascope_backend.api.lib.exceptions.api_exceptions import NotFoundException
from mascope_backend.api.controllers.target.lib.compute.target_ions_compute import (
    generate_target_ions_from_composition,
    generate_target_ions_from_mass,
)
from mascope_backend.api.controllers.match.aggregate.match_aggregate_controller import (
    aggregate_and_recreate_matches,
)
from mascope_backend.api.models.target.compounds.target_compound_pydantic_model import (
    TargetCompoundBase,
)
from mascope_backend.api.models.target.ions.target_ion_pydantic_model import (
    TargetIonUpdate,
)
from mascope_backend.api.new.ionization.modes.util import (
    fetch_batch_ionization_mechanism_ids,
)


@api_controller()
async def get_target_ions(
    target_compound_id: str = None,
    ionization_mechanism_id: str = None,
    sample_batch_id: Optional[str] = None,
    target_collection_id: Optional[str] = None,
    show_target_collection: bool = False,
    show_ionization_mechanism: bool = False,
    target_compound_ids: Optional[List[str]] = None,
    ionization_mechanism_ids: Optional[List[str]] = None,
    target_ion_formula: str = None,
    sort: str = None,
    order: str = None,
    page: int | None = None,
    limit: int | None = None,
) -> dict:
    """
    Retrieves a paginated list of target ions based on various filtering criteria such as target compound,
    ionization mechanism, sample batch, and specific ion formulas. Results can optionally include related
    target collection information and can be ordered and sorted according to specified parameters.

    Steps:
    - Construct the base query for fetching target ions.
    - Apply filters based on target compound ID, ionization mechanism ID, compound list, and ionization mechanism list.
    - If additional context such as sample batch or target collection details are requested, enhance the query to join
       with related tables and filter further based on these details.
    - If 'show_target_collection' or 'show_ionization_mechanism' is true, join with the respective tables to include
       these details in the results.
    - Apply ordering and sorting to the query.
    - Execute the query with pagination.
    - Format the fetched data into a list of dictionaries suitable for JSON serialization and return alongside total results count.

    :param target_compound_id: Filter by specific target compound ID, defaults to None.
    :type target_compound_id: str | None
    :param ionization_mechanism_id: Filter by specific ionization mechanism ID, defaults to None.
    :type ionization_mechanism_id: str | None
    :param sample_batch_id: Filter ions by the ID of the associated sample batch, defaults to None.
    :type sample_batch_id: Optional[str]
    :param target_collection_id: Filter ions by the ID of the target collection they belong to, defaults to None.
    :type target_collection_id: Optional[str]
    :param show_target_collection: Include detailed target collection data in the results, defaults to False.
    :type show_target_collection: bool
    :param show_ionization_mechanism: Include ionization mechanism data in the results, defaults to False.
    :type show_ionization_mechanism: bool
    :param target_compound_ids: List of target compound IDs for broader filtering, defaults to None.
    :type target_compound_ids: Optional[List[str]]
    :param ionization_mechanism_ids: List of ionization mechanism IDs for broader filtering, defaults to None.
    :type ionization_mechanism_ids: Optional[List[str]]
    :param target_ion_formula: Filter ions by their chemical formula, defaults to None.
    :type target_ion_formula: str | None
    :param sort: Field name to sort the results by, defaults to None.
    :type sort: str | None
    :param order: Sorting order, either 'asc' or 'desc', defaults to None.
    :type order: str | None
    :param page: Page number for pagination, defaults to None (no pagination).
    :type page: int | None
    :param limit: Number of items per page, defaults to None (no pagination).
    :type limit: int | None
    :return: A dictionary containing the total number of results and a list of target ions.
    :rtype: dict
    """
    # Validate pagination parameters
    if (page is None) != (limit is None):
        raise ValueError(
            "Both 'page' and 'limit' must be provided together or both omitted."
        )
    async with async_session() as session:
        # Construct the base query
        stmt = select(TargetIon)

        # Apply basic filters
        if target_compound_id:
            stmt = stmt.filter(TargetIon.target_compound_id == target_compound_id)
        if ionization_mechanism_id:
            stmt = stmt.filter(
                TargetIon.ionization_mechanism_id == ionization_mechanism_id
            )
        if target_compound_ids:
            stmt = stmt.filter(TargetIon.target_compound_id.in_(target_compound_ids))
        if ionization_mechanism_ids:
            stmt = stmt.filter(
                TargetIon.ionization_mechanism_id.in_(ionization_mechanism_ids)
            )
        if target_ion_formula:
            stmt = stmt.filter(TargetIon.target_ion_formula == target_ion_formula)

        # Adjust the query based non-basic filters
        if sample_batch_id or target_collection_id or show_target_collection:
            stmt = stmt.join(
                TargetCompoundInTargetCollection,
                TargetCompoundInTargetCollection.target_compound_id
                == TargetIon.target_compound_id,
            )

            # Filter ions by sample_batch_id if specified
            if sample_batch_id:
                # Fetch sample batch and related ion mechanisms and target collection ids
                result = await session.execute(
                    select(SampleBatch)
                    .options(joinedload(SampleBatch.target_collection))
                    .where(SampleBatch.sample_batch_id == sample_batch_id)
                )
                sample_batch = result.unique().scalar_one_or_none()
                if not sample_batch:
                    raise NotFoundException(
                        f"Sample batch with id '{sample_batch_id}' not found"
                    )

                # Extract ion mechanisms
                ionization_mechanism_ids = await fetch_batch_ionization_mechanism_ids(
                    sample_batch_id
                )
                target_collection_ids = [
                    tc.target_collection_id for tc in sample_batch.target_collection
                ]

                # Filter ions by batch ionization_mechanism_ids and target_collection_ids
                stmt = stmt.where(
                    TargetCompoundInTargetCollection.target_collection_id.in_(
                        target_collection_ids
                    ),
                    TargetIon.ionization_mechanism_id.in_(ionization_mechanism_ids),
                ).distinct()

            # Filter ions by target_collection_id if specified
            if target_collection_id:
                stmt = stmt.filter(
                    TargetCompoundInTargetCollection.target_collection_id
                    == target_collection_id
                )

            # Include target collection details if requested
            if show_target_collection:
                stmt = stmt.join(
                    TargetCollection,
                    TargetCollection.target_collection_id
                    == TargetCompoundInTargetCollection.target_collection_id,
                )
                stmt = stmt.add_columns(
                    TargetCompoundInTargetCollection.target_collection_id,
                    TargetCollection.target_collection_name,
                    TargetCollection.target_collection_type,
                )

        # Join IonizationMechanism if show_ionization_mechanism is True
        if show_ionization_mechanism:
            stmt = stmt.join(
                IonizationMechanism,
                IonizationMechanism.ionization_mechanism_id
                == TargetIon.ionization_mechanism_id,
            )
            stmt = stmt.add_columns(
                IonizationMechanism.ionization_mechanism,
            )

        # Apply sorting
        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(TargetIon, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(TargetIon, sort)))

        # Get total count
        total = await session.scalar(
            select(func.count()).select_from(stmt)  # pylint: disable=not-callable
        )
        # Apply pagination conditionally
        if page is not None and limit is not None:
            stmt = stmt.offset(page * limit).limit(limit)
        result = await session.execute(stmt)

    # Construct the response data
    data = []
    for row in result.all():
        # When show_target_collection is true, include target_collection_id
        ion_data = row.TargetIon.to_dict()
        if show_target_collection and row.target_collection_id:
            ion_data["target_collection_id"] = row.target_collection_id
            ion_data["target_collection_name"] = row.target_collection_name
            ion_data["target_collection_type"] = row.target_collection_type
        if show_ionization_mechanism:
            ion_data["ionization_mechanism"] = row.ionization_mechanism
        data.append(ion_data)

    return {
        "message": "Target ions retrieved successfully.",
        "results": total,
        "data": data,
    }


@api_controller()
async def get_target_ion(target_ion_id: str) -> dict:
    """
    Retrieves a single target ion by its unique ID.

    Steps:
    1. Execute a query to fetch the target ion with the specified ID.
    2. Check if the target ion exists. If not, raise a NotFoundException.
    3. Return the target ion's details as a dictionary.

    :param target_ion_id: Unique identifier of the target ion to retrieve.
    :raises NotFoundException: If the target ion with the given ID is not found.
    :return: The requested target ion's details.
    """
    async with async_session() as session:
        # Step 1: Fetch target ion by ID
        target_ion = await session.get(TargetIon, target_ion_id)

        # Step 2: If target ion not found, raise exception
        if not target_ion:
            raise NotFoundException(f"Target ion with ID '{target_ion_id}' not found")

        # Step 3: Return target ion details
        return {
            "message": "Target ion retrieved successfully.",
            "data": target_ion.to_dict(),
        }


@api_controller()
async def create_target_ions(
    target_compound: TargetCompoundBase,
    ionization_mechanisms: List[IonizationMechanism],
    target_compound_mass: float = None,
    independent_transaction=False,
    session=None,
) -> dict:
    """Function to create target ion and target isotope records
    derived from a given target compound and list of ionization mechanisms to apply.
    If target compound mass is given, it will be used instead of compound formula.

    Steps:
    1. Verify input parameters and initialize session if operation is an independent transaction.
    2. Generate target ions and isotopes based on compound formula or mass.
    3. Persist the generated ions and isotopes in the database.
    4. Return created ions, isotopes, and any message logs.

    :param target_compound: Target compound to derive ions and isotopes from
    :type target_compound: TargetCompoundBase
    :param ionization_mechanisms: List of ionization mechanisms to apply to the compound
    :type ionization_mechanisms: List[IonizationMechanism]
    :param target_compound_mass: Mass of the target compound (if formula is not known),
    defaults to None. If None, formula will be used.
    :type target_compound_mass: float, optional
    :param independent_transaction: Flag indicating whether the create target ions is an independent transaction, defaults to False
    :type independent_transaction: bool, optional
    :param session: Database session, smust be gicen if not an independent transaction, defaults to None
    :type session: SQLAlchemy.AsyncSession, optional
    :return: Dictionary with created ions, isotopes, and message logs.
    :rtype: dict
    """
    # Step 1: Initialize session if operation is an independent transaction.
    if independent_transaction:
        session = async_session()

    # Step 2: Generate target ions and isotopes
    if target_compound_mass is None:
        # Parsing into float failed, target compound is given by composition
        (
            target_ions,
            target_isotopes,
        ) = generate_target_ions_from_composition(
            target_compound, ionization_mechanisms
        )
    else:
        # Try if target compound is given by mass (try to parse composition into float)
        target_compound_mass = float(target_compound.target_compound_formula)
        (
            target_ions,
            target_isotopes,
        ) = generate_target_ions_from_mass(
            target_compound_mass, target_compound, ionization_mechanisms
        )

    # Step 3: Persist generated ions and isotopes
    for target_isotope in target_isotopes:
        # Add the isotopes to be committed to the db
        session.add(target_isotope)
    for target_ion in target_ions:
        # Add the ions to be committed to the db
        session.add(target_ion)

    if independent_transaction:
        await session.commit()
    else:
        await session.flush()

    # Step 4: Return created entities and message logs
    return {
        "created_ions": [ion.to_dict() for ion in target_ions],
        "created_isotopes": [isotope.to_dict() for isotope in target_isotopes],
        "message_logs": {},  # TODO_target_compound_management Populate with relevant log messages
    }


@api_controller()
async def update_target_ion(target_ion_id: str, target_ion_update: TargetIonUpdate):
    async with async_session() as session:
        target_ion = await session.get(TargetIon, target_ion_id)
        if not target_ion:
            raise NotFoundException(f"Target ion with ID '{target_ion_id}' not found")

        existing_match_params = target_ion.filter_params or {}

        # Create a new dictionary for updated match params
        new_match_params = existing_match_params.copy()
        affected_instruments = set()

        # Handle deletion of filter parameters for a specific instrument
        if target_ion_update.delete_instrument_params:
            instrument_to_delete = target_ion_update.delete_instrument_params
            if instrument_to_delete in new_match_params:
                del new_match_params[instrument_to_delete]
                target_ion.filter_params = new_match_params
                affected_instruments.add(instrument_to_delete)

        # Handle updating filter parameters
        else:
            updated_match_params = target_ion_update.match_params
            for instrument, update_params in updated_match_params.items():
                update_params_dict = update_params.model_dump()
                # Check for changes in match params
                if (
                    instrument not in existing_match_params
                    or existing_match_params[instrument] != update_params_dict
                ):
                    new_match_params[instrument] = update_params_dict
                    affected_instruments.add(instrument)

                    # update record params
                    target_ion.filter_params = new_match_params

        # Commit and refresh if there are any changes
        if affected_instruments:
            await session.commit()
            await session.refresh(target_ion)

            # Find and notify affected sample batches
            for instrument in affected_instruments:
                stmt = (
                    select(SampleBatch.sample_batch_id)
                    .join(Sample)
                    .join(TargetCollectionInSampleBatch)
                    .join(TargetCollection)
                    .join(TargetCompoundInTargetCollection)
                    .join(TargetCompound)
                    .join(TargetIon)
                    .where(TargetIon.target_ion_id == target_ion_id)
                    # Filter sample batches by instrument
                    .where(Sample.instrument == instrument)
                    .distinct()
                )
                result = await session.execute(stmt)
                affected_batches = result.fetchall()
                affected_batch_ids = [
                    batch.sample_batch_id for batch in affected_batches
                ]

                for sample_batch_id in affected_batch_ids:
                    await aggregate_and_recreate_matches(
                        sample_batch_id=sample_batch_id,
                    )

        return {
            "data": target_ion.to_dict(),
            "message": f"Target ion `{target_ion.target_ion_formula}` updated successfully.",
        }
