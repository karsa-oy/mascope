# pylint: disable=not-callable
"""
Ionization mechanisms controller for managing ionization mechanism operations.
"""
from fastapi import HTTPException
from sqlalchemy import (
    select,
    asc,
    desc,
    func,
    delete,
)
from mascope_backend.socket.records.service import (
    emit_record_created,
    emit_record_deleted,
)
from mascope_backend.db import async_session
from mascope_backend.db.id import gen_id
from mascope_backend.db.models import (
    IonizationMechanism,
    IonizationMode,
    TargetCompound,
    TargetIon,
    TargetIsotope,
    SampleBatch,
    SampleItem,
)
from mascope_backend.api.lib.api_features import api_controller
from mascope_backend.api.lib.exceptions.api_exceptions import (
    ApiException,
    NotFoundException,
)
from mascope_backend.api.controllers.target.ions.target_ions_controller import (
    create_target_ions,
)
from mascope_backend.api.models.ionization_mechanisms.ionization_mechanism_pydantic_model import (
    IonizationMechanismCreate,
    IonizationMechanismRead,
)


@api_controller()
async def get_ionization_mechanisms(
    ionization_mechanism_polarity: str | None = None,
    ionization_mechanism: list | None = None,
    reagent: str | None = None,
    is_default: bool | None = None,
    sort: str | None = None,
    order: str | None = None,
    page: int | None = None,
    limit: int | None = None,
) -> dict:
    """
    Retrieves a paginated list of ionization mechanisms, optionally filtered by polarity, mechanism, or reagent,
    and sorted by a specified column.

    Steps:
    1. Construct a SQLAlchemy query to select all ionization mechanisms.
    2. Apply filtering based on provided parameters.
    3. Apply sorting based on the provided sort and order parameters.
    4. Apply pagination based on the provided page and limit parameters.
    5. Execute the query and fetch the results.
    6. Convert the results into a list of dictionaries for JSON serialization.

    :param ionization_mechanism_polarity: Filter by polarity, defaults to None.
    :param ionization_mechanism: Filter by mechanism, defaults to None.
    :type ionization_mechanism: list | None
    :param reagent: Filter by reagent, defaults to None.
    :param is_default: Filter by default acquisition ionization mechanism, defaults to None.
    :type is_default: bool | None
    :param sort: Column to sort by, defaults to None.
    :param order: Sorting order, defaults to None.
    :param page: Page number for pagination, defaults to None (no pagination).
    :param limit: Number of items per page, defaults to None (no pagination).
    :return: A dictionary with the total count and a list of ionization mechanisms.
    """
    # Validate pagination parameters
    if (page is None) != (limit is None):
        raise ValueError(
            "Both 'page' and 'limit' must be provided together or both omitted."
        )
    async with async_session() as session:
        stmt = select(IonizationMechanism)

        # Step 2: Apply filters if specified
        if ionization_mechanism_polarity:
            stmt = stmt.filter(
                IonizationMechanism.ionization_mechanism_polarity
                == ionization_mechanism_polarity
            )
        if ionization_mechanism:
            stmt = stmt.where(
                IonizationMechanism.ionization_mechanism.in_(ionization_mechanism)
            )
        if reagent:
            stmt = stmt.filter(IonizationMechanism.reagent == reagent)

        if is_default is not None:
            stmt = stmt.filter(
                IonizationMechanism.is_default == (1 if is_default else 0)
            )

        # Step 3: Apply sorting
        if sort:
            sort_expression = (
                desc(getattr(IonizationMechanism, sort))
                if order == "desc"
                else asc(getattr(IonizationMechanism, sort))
            )
            stmt = stmt.order_by(sort_expression)

        # Step 4: Apply pagination
        total = await session.scalar(select(func.count()).select_from(stmt))
        if page is not None and limit is not None:
            stmt = stmt.offset(page * limit).limit(limit)
        # Step 5: Execute the query
        result = await session.execute(stmt)
        ionization_mechanisms = result.scalars().all()

        # Step 6: Return results
        return {
            "message": "Retrieved ionization mechanisms successfully.",
            "results": total,
            "data": [
                IonizationMechanismRead.model_validate(
                    ionization_mechanism
                ).model_dump()
                for ionization_mechanism in ionization_mechanisms
            ],
        }


@api_controller()
async def get_ionization_mechanism(ionization_mechanism_id: str) -> dict:
    """
    Retrieves a single ionization mechanism by its unique ID.

    Steps:
    1. Execute a query to fetch the ionization mechanism with the specified ID.
    2. Check if the ionization mechanism exists. If not, raise a NotFoundException.
    3. Return the ionization mechanism's details as a dictionary.

    :param ionization_mechanism_id: Unique identifier of the ionization mechanism to retrieve.
    :raises NotFoundException: If the ionization mechanism with the given ID is not found.
    :return: The requested ionization mechanism's details.
    """
    async with async_session() as session:
        # Step 1: Fetch ionization mechanism by ID
        ionization_mechanism = await session.get(
            IonizationMechanism, ionization_mechanism_id
        )

        # Step 2: If ionization mechanism not found, raise exception
        if not ionization_mechanism:
            raise NotFoundException(
                f"Ionization mechanism with ID '{ionization_mechanism_id}' not found"
            )

        # Step 3: Retrieve ionization modes -> sample items -> sample batches
        #         using the specified ionization mechanism
        affected_ion_mode_ids = []
        result = await session.execute(select(IonizationMode))
        all_ion_modes = result.scalars().all()
        for ion_mode in all_ion_modes:
            if ionization_mechanism_id in ion_mode.ionization_mechanism_ids:
                affected_ion_mode_ids.append(ion_mode.ionization_mode_id)

        result = await session.execute(
            select(SampleItem).where(
                SampleItem.ionization_mode_id.in_(affected_ion_mode_ids)
            )
        )
        affected_sample_items = result.scalars().all()

        affected_sample_batch_ids = list(
            set(item.sample_batch_id for item in affected_sample_items)
        )
        result = await session.execute(
            select(SampleBatch).where(
                SampleBatch.sample_batch_id.in_(affected_sample_batch_ids)
            )
        )
        affected_sample_batches = result.scalars().all()
        affected_sample_batch_info = [
            {
                "sample_batch_id": batch.sample_batch_id,
                "sample_batch_name": batch.sample_batch_name,
            }
            for batch in affected_sample_batches
        ]

        # Step 4: Return ionization mechanism details with sample batches
        ionization_mechanism_data = IonizationMechanismRead.model_validate(
            ionization_mechanism
        ).model_dump()
        ionization_mechanism_data["sample_batches_count"] = len(affected_sample_batches)
        ionization_mechanism_data["sample_batches"] = affected_sample_batch_info
        return {
            "message": f"Ionization mechanism '{ionization_mechanism.ionization_mechanism}' retrieved successfully.",
            "data": ionization_mechanism_data,
        }


@api_controller()
async def create_ionization_mechanism(
    ionization_mechanism_create: IonizationMechanismCreate,
) -> dict:
    """
    Creates a new ionization mechanism and generates corresponding ions for each existing target compound in the database.

    Steps:
    1. Check if the ionization mechanism already exists using the get_ionization_mechanisms function.
    2. Create a new ionization mechanism instance and add it to the session.
    3. Fetch all target compounds from the database.
    4. For each target compound, create target ions with the new ionization mechanism.
    5. Commit the transaction to persist changes to the database.
    6. Return the created ionization mechanism's details with a success message.

    :param ionization_mechanism: Ionization mechanism to create
    :type ionization_mechanism: IonizationMechanismCreate
    :raises HTTPException: If the ionization mechanism already exists.
    :raises NotFoundException: If the ionization mechanism is not found after creation.
    :return: Created ionization mechanism details.
    :rtype: dict
    """
    # Step 1: Check if the ionization mechanism already exists
    existing_mechanisms = await get_ionization_mechanisms(
        ionization_mechanism=[ionization_mechanism_create.ionization_mechanism]
    )

    if existing_mechanisms["results"] != 0:
        raise HTTPException(
            status_code=409,
            detail=f"Ionization mechanism '{ionization_mechanism_create.ionization_mechanism}' already exists",
        )

    # Step 2: Create a new ionization mechanism instance and add it to the session.
    async with async_session() as session:
        new_ionization_mechanism = IonizationMechanism(
            ionization_mechanism_id=gen_id(11),
            **ionization_mechanism_create.model_dump(),
        )
        session.add(new_ionization_mechanism)

        # Step 3: Fetch all target compounds
        stmt = select(TargetCompound)
        result = await session.execute(stmt)
        target_compounds = result.scalars().all()

        # Step 4: Create target ions with new mechanism for each compound
        for target_compound in target_compounds:
            try:
                # Try if target compound is given by mass (try to parse composition into float)
                target_compound_mass = float(target_compound.target_compound_formula)
            except ValueError:
                target_compound_mass = None

            # Create target ions for the compound
            await create_target_ions(
                target_compound=target_compound,
                ionization_mechanisms=[new_ionization_mechanism],
                target_compound_mass=target_compound_mass,
                independent_transaction=False,
                session=session,
            )

        # Step 5: Commit the transaction
        await session.commit()
        await session.refresh(new_ionization_mechanism)

    if not new_ionization_mechanism:
        raise NotFoundException(
            f"Ionization mechanism with ID '{new_ionization_mechanism.ionization_mechanism_id}' not found after it should have been created"
        )
    ionization_mechanism_data = IonizationMechanismRead.model_validate(
        new_ionization_mechanism
    ).model_dump()

    # Step 6: Emit creation event
    await emit_record_created(
        record_type="ionization_mechanism",
        record_id=new_ionization_mechanism.ionization_mechanism_id,
        record=ionization_mechanism_data,
    )

    # Step 7: Return created ionization mechanism details with a success message
    return {
        "message": f"Ionization mechanism '{new_ionization_mechanism.ionization_mechanism}' was created successfully.",
        "data": ionization_mechanism_data,
    }


@api_controller()
async def delete_ionization_mechanism(ionization_mechanism_id: str) -> dict:
    """
    Deletes an ionization mechanism by its ID, ensuring it's not used by any sample batches.

    Steps:
    1. Retrieve the ionization mechanism along with any referencing sample batches.
    2. If no sample batches use this ionization mechanism, delete related TargetIsotope and TargetIon records.
    3. Delete the ionization mechanism from the database.
    4. If referenced, throw an ApiException preventing deletion.

    :param ionization_mechanism_id: The unique identifier of the ionization mechanism to delete.
    :type ionization_mechanism_id: str
    :raises ApiException: If the ionization mechanism is referenced in any sample batch.
    :raises NotFoundException: If no ionization mechanism is found with the provided ID.
    :return: Deleted ionization mechanism message.
    :rtype: dict
    """
    # Step 1: Fetch the ionization mechanism
    async with async_session() as session:
        ionization_mechanism = await session.get(
            IonizationMechanism, ionization_mechanism_id
        )
        if not ionization_mechanism:
            raise NotFoundException(
                f"Ionization mechanism with ID '{ionization_mechanism_id}' not found"
            )

        # Step 2: Retrieve the ionization mechanism and check for sample batch references
        ionization_data = await get_ionization_mechanism(ionization_mechanism_id)
        ionization_details = ionization_data.get("data")
        if ionization_details["sample_batches_count"] > 0:
            raise ApiException(
                f"Ionization mechanism '{ionization_mechanism.ionization_mechanism}' cannot be deleted as it is used in {ionization_details['sample_batches_count']} sample batches.",
                {"sample_batches": ionization_details["sample_batches"]},
                400,
            )

        # Step 3: Manually delete related TargetIsotope and TargetIon records

        # Delete TargetIsotope records
        delete_target_isotope_query = delete(TargetIsotope).where(
            TargetIsotope.target_ion_id.in_(
                select(TargetIon.target_ion_id).where(
                    TargetIon.ionization_mechanism_id == ionization_mechanism_id
                )
            )
        )

        await session.execute(delete_target_isotope_query)

        # Delete TargetIon records
        delete_target_ion_query = delete(TargetIon).where(
            TargetIon.ionization_mechanism_id == ionization_mechanism_id
        )
        await session.execute(delete_target_ion_query)

        # Delete the IonizationMechanism record
        delete_ionization_mechanism_query = delete(IonizationMechanism).where(
            IonizationMechanism.ionization_mechanism_id == ionization_mechanism_id
        )
        await session.execute(delete_ionization_mechanism_query)

        # Commit the transaction
        await session.commit()

    # Step 4: Emit deletion event
    await emit_record_deleted(
        record_type="ionization_mechanism",
        record_id=ionization_mechanism_id,
    )

    return {
        "message": f"Ionization mechanism '{ionization_mechanism.ionization_mechanism}' was deleted successfully."
    }
