from typing import List, Optional
from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import joinedload
from mascope_lib.molmass import Formula
from mascope_server.db import async_session
from mascope_server.api_sio import sio
from mascope_server.db.id import gen_id
from mascope_server.api.utils.api_features import api_controller
from mascope_server.api.exceptions import NotFoundException
from mascope_server.api.models.models import (
    IonizationMechanism,
    TargetIon,
    TargetIsotope,
    TargetCompound,
    TargetCollection,
    TargetCompoundInTargetCollection,
    TargetCollectionInSampleBatch,
    SampleBatch,
    Sample,
)
from mascope_server.api.models.pydantic_models.target_compound_pydantic_model import (
    TargetCompoundBase,
)
from mascope_server.api.models.pydantic_models.target_ion_pydantic_model import (
    TargetIonUpdate,
)


@api_controller()
async def get_target_ions(
    target_compound_id: str = None,
    ionization_mechanism_id: str = None,
    sample_batch_id: Optional[str] = None,
    target_collection_id: Optional[str] = None,
    show_target_collection: bool = False,
    target_compound_ids: Optional[List[str]] = None,
    ionization_mechanism_ids: Optional[List[str]] = None,
    target_ion_formula: str = None,
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 10000,
) -> dict:
    """
    Retrieves a paginated list of target ions based on various filtering criteria such as target compound,
    ionization mechanism, sample batch, and specific ion formulas. Results can optionally include related
    target collection information and can be ordered and sorted according to specified parameters.

    Steps:
    1. Construct the base query for fetching target ions.
    2. Apply filters based on target compound ID, ionization mechanism ID, compound list, and ionization mechanism list.
    3. If additional context such as sample batch or target collection details are requested, enhance the query to join
       with related tables and filter further based on these details.
    4. If 'show_target_collection' is true, join with the target collection table to include these details in the results.
    5. Apply ordering and sorting to the query.
    6. Execute the query with pagination.
    7. Format the fetched data into a list of dictionaries suitable for JSON serialization and return alongside total results count.

    :param target_compound_id: Filter by specific target compound ID, defaults to None.
    :type target_compound_id: Optional[str]
    :param ionization_mechanism_id: Filter by specific ionization mechanism ID, defaults to None.
    :type ionization_mechanism_id: Optional[str]
    :param sample_batch_id: Filter ions by the ID of the associated sample batch, defaults to None.
    :type sample_batch_id: Optional[str]
    :param target_collection_id: Filter ions by the ID of the target collection they belong to, defaults to None.
    :type target_collection_id: Optional[str]
    :param show_target_collection: Include detailed target collection data in the results, defaults to False.
    :type show_target_collection: bool
    :param target_compound_ids: List of target compound IDs for broader filtering, defaults to None.
    :type target_compound_ids: Optional[List[str]]
    :param ionization_mechanism_ids: List of ionization mechanism IDs for broader filtering, defaults to None.
    :type ionization_mechanism_ids: Optional[List[str]]
    :param target_ion_formula: Filter ions by their chemical formula, defaults to None.
    :type target_ion_formula: Optional[str]
    :param sort: Field name to sort the results by, defaults to None.
    :type sort: Optional[str]
    :param order: Sorting order, either 'asc' or 'desc', defaults to None.
    :type order: Optional[str]
    :param page: Page number for pagination, defaults to 0.
    :type page: int
    :param limit: Number of items per page, defaults to 10000.
    :type limit: int
    :return: A dictionary containing the total number of results and a list of target ions.
    :rtype: dict
    """
    async with async_session() as session:
        # Step 1: Construct the base query
        stmt = select(TargetIon)

        # Step 2: Apply basic filters
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

        # Step 3: Adjust the query based non-basic filters
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
                ionization_mechanism_ids = sample_batch.build_params["ion_mechanisms"]
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

            # Step 4: Include target collection details if requested
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

        # Step 5: Apply sorting
        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(TargetIon, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(TargetIon, sort)))

        # Get total count
        total = await session.scalar(
            select(func.count()).select_from(stmt)  # pylint: disable=not-callable
        )
        # Step 4: Apply pagination
        stmt = stmt.offset(page * limit).limit(limit)
        # Step 6: Execute the query
        result = await session.execute(stmt)

    # Step 7: Construct the response data
    data = []
    for row in result.all():
        # When show_target_collection is true, include target_collection_id
        ion_data = row.TargetIon.to_dict()
        if show_target_collection and row.target_collection_id:
            ion_data["target_collection_id"] = row.target_collection_id
            ion_data["target_collection_name"] = row.target_collection_name
            ion_data["target_collection_type"] = row.target_collection_type
        data.append(ion_data)

    return {
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
        return target_ion.to_dict()


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
    2. Define helper functions for ion and isotope generation.
    3. Generate target ions and isotopes based on compound formula or mass.
    4. Persist the generated ions and isotopes in the database.
    5. Return created ions, isotopes, and any message logs.

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

    # Step 2: Define helper functions for ion and isotope generation.
    def charge_string(raw_ion: Formula) -> str:
        """Get charge string (+/-) based on ion formula

        :param raw_ion: Formula instance of the ion
        :type raw_ion: Formula
        :return: Charge string, either + or -
        :rtype: str
        """
        if raw_ion.charge == -1:
            charge_string = "-"
        elif raw_ion.charge == +1:
            charge_string = "+"
        else:
            charge_string = ""
        return charge_string

    def generate_target_ions_from_composition(
        target_compound: TargetCompoundBase,
        ionization_mechanisms: List[IonizationMechanism],
    ) -> tuple:
        """Generate target ions and isotopes based on target compound composition and given ionization mechanisms

        :param target_compound: Target compound to use as a base for the ions
        :type target_compound: TargetCompoundBase
        :param ionization_mechanisms: List of ionization mechanisms to apply to the target compound
        :type ionization_mechanisms: List[IonizationMechanism]
        :return: 2-tuple of (list of ions (instances of TargetIon), list of isotopes (instances of TargetIsotope))
        :rtype: tuple
        """
        target_ions = []
        target_isotopes = []

        # generate and create ion records
        for ionization_mechanism in ionization_mechanisms:
            mechanism = ionization_mechanism.ionization_mechanism
            try:
                # get and save ions
                raw_ion = Formula(
                    "("
                    + target_compound.target_compound_formula.rstrip()
                    + mechanism[:-1]  # remove polarity sign before parenthesis
                    + ")"
                    + mechanism[-1]  # add polarity sign at the end
                )
            except ValueError as e:
                raise ValueError("Failed to parse ion formula: %s" % e)
            else:
                # construct and save ion row
                ion = TargetIon(
                    target_ion_id=gen_id(16),
                    target_compound_id=target_compound.target_compound_id,
                    ionization_mechanism_id=ionization_mechanism.ionization_mechanism_id,
                    target_ion_formula=raw_ion.formula + charge_string(raw_ion),
                    filter_params={},
                )

                target_ions.append(ion)

                # construct and save isotope rows
                raw_isotopes = raw_ion.mz_spectrum().values()
                target_isotopes.extend(
                    [
                        TargetIsotope(
                            target_isotope_id=gen_id(16),
                            target_ion_id=ion.target_ion_id,
                            mz=mz,
                            relative_abundance=rel_abu,
                        )
                        for mz, rel_abu in raw_isotopes
                    ]
                )
        return target_ions, target_isotopes

    def generate_target_ions_from_mass(
        target_compound_mass: float,
        target_compound: TargetCompoundBase,
        ionization_mechanisms: List[IonizationMechanism],
    ) -> tuple:
        """Generate target ions and isotopes based on target compound mass and given ionization mechanisms

        :param target_compound_mass: Mass of the target compound (composition not known)
        :type target_compound_mass: float
        :param target_compound: Target compound to use as a base for the ions
        :type target_compound: TargetCompoundBase
        :param ionization_mechanisms: List of ionization mechanisms to apply to the target compound
        :type ionization_mechanisms: List[IonizationMechanism]
        :return: 2-tuple of (list of ions (instances of TargetIon), list of isotopes (instances of TargetIsotope))
        :rtype: tuple
        """
        target_ions = []
        target_isotopes = []

        # generate and create ion records
        for ionization_mechanism in ionization_mechanisms:
            mechanism = ionization_mechanism.ionization_mechanism
            # construct and save ion row
            ion = TargetIon(
                target_ion_id=gen_id(16),
                target_compound_id=target_compound.target_compound_id,
                ionization_mechanism_id=ionization_mechanism.ionization_mechanism_id,
                target_ion_formula=(f"{target_compound_mass:.4f}" + mechanism),
                filter_params={},
            )

            target_ions.append(ion)
            # construct and save isotope rows
            raw_ion = Formula("(" + mechanism[1:-1] + ")" + mechanism[-1])
            is_adduct = mechanism[0] == "+"
            if is_adduct:
                raw_isotopes = raw_ion.mz_spectrum().values()
            else:
                raw_isotopes = [
                    (-raw_ion.mz, 1.0)  # pylint: disable=invalid-unary-operand-type
                ]

            target_isotopes.extend(
                [
                    TargetIsotope(
                        target_isotope_id=gen_id(16),
                        target_ion_id=ion.target_ion_id,
                        mz=(target_compound_mass + reagent_mz),
                        relative_abundance=reagent_rel_abu,
                    )
                    for reagent_mz, reagent_rel_abu in raw_isotopes
                ]
            )

        return target_ions, target_isotopes

    # Step 3: Generate target ions and isotopes
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

    # Step 4: Persist generated ions and isotopes
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

    # Step 5: Return created entities and message logs
    return {
        "created_ions": [ion.to_dict() for ion in target_ions],
        "created_isotopes": [isotope.to_dict() for isotope in target_isotopes],
        "message_logs": {},  # TODO_target_compound_management Populate with relevant log messages
    }


async def update_target_ion(target_ion_id: str, target_ion_update: TargetIonUpdate):
    async with async_session() as session:
        target_ion = await session.get(TargetIon, target_ion_id)
        if not target_ion:
            raise NotFoundException(f"Target ion with ID '{target_ion_id}' not found")

        existing_filter_params = target_ion.filter_params or {}

        # Create a new dictionary for updated filter_params
        new_filter_params = existing_filter_params.copy()
        affected_instruments = set()

        # Handle deletion of filter parameters for a specific instrument
        if target_ion_update.delete_instrument_filters:
            instrument_to_delete = target_ion_update.delete_instrument_filters
            if instrument_to_delete in new_filter_params:
                del new_filter_params[instrument_to_delete]
                target_ion.filter_params = new_filter_params
                affected_instruments.add(instrument_to_delete)

        # Handle updating filter parameters
        else:
            updated_filter_params = target_ion_update.filter_params
            for instrument, update_params in updated_filter_params.items():
                update_params_dict = update_params.dict()
                # Check for changes in filter_params
                if (
                    instrument not in existing_filter_params
                    or existing_filter_params[instrument] != update_params_dict
                ):
                    new_filter_params[instrument] = update_params_dict
                    affected_instruments.add(instrument)

                    # Assign the new dictionary to target_ion.filter_params
                    target_ion.filter_params = new_filter_params

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

                # Emit signal for affected sample batches
                for sample_batch_id in affected_batch_ids:
                    await sio.emit(
                        "sample_batch_reload",
                        room=sample_batch_id,
                        namespace="/",
                    )

        return target_ion.to_dict()
