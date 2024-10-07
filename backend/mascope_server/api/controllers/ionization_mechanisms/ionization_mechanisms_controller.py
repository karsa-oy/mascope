from sqlalchemy import (
    select,
    asc,
    desc,
    func,
    delete,
)
from mascope_server.app import sio
from mascope_server.db import async_session
from mascope_server.db.id import gen_id
from mascope_server.db.models import (
    IonizationMechanism,
    TargetCompound,
    TargetIon,
    TargetIsotope,
    SampleBatch,
)
from mascope_server.api.lib.api_features import api_controller
from mascope_server.api.lib.exceptions.api_exceptions import (
    ApiException,
    NotFoundException,
)
from mascope_server.api.controllers.target.ions.target_ions_controller import (
    create_target_ions,
)
from mascope_server.api.models.ionization_mechanisms.ionization_mechanism_pydantic_model import (
    IonizationMechanismCreate,
)


@api_controller()
async def get_ionization_mechanisms(
    ionization_mechanism_polarity: str = None,
    ionization_mechanism: str = None,
    reagent: str = None,
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 10000,
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
    :param reagent: Filter by reagent, defaults to None.
    :param sort: Column to sort by, defaults to None.
    :param order: Sorting order, defaults to None.
    :param page: Page number for pagination, defaults to 0.
    :param limit: Number of items per page, defaults to 100.
    :return: A dictionary with the total count and a list of ionization mechanisms.
    """
    async with async_session() as session:
        stmt = select(IonizationMechanism)

        # Step 2: Apply filters if specified
        if ionization_mechanism_polarity:
            stmt = stmt.filter(
                IonizationMechanism.ionization_mechanism_polarity
                == ionization_mechanism_polarity
            )
        if ionization_mechanism:
            stmt = stmt.filter(
                IonizationMechanism.ionization_mechanism == ionization_mechanism
            )
        if reagent:
            stmt = stmt.filter(IonizationMechanism.reagent == reagent)

        # Step 3: Apply sorting
        if sort:
            sort_expression = (
                desc(getattr(IonizationMechanism, sort))
                if order == "desc"
                else asc(getattr(IonizationMechanism, sort))
            )
            stmt = stmt.order_by(sort_expression)

        # Step 4: Apply pagination
        total = await session.scalar(
            select(func.count()).select_from(stmt)  # pylint: disable=not-callable
        )
        stmt = stmt.offset(page * limit).limit(limit)
        # Step 5: Execute the query
        result = await session.execute(stmt)
        ionization_mechanisms = result.scalars().all()

        # Step 6: Return results
        return {
            "total": total,
            "data": [
                ionization_mechanism.to_dict()
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

        # Step 3: Retrieve sample batches using the specified ionization mechanism
        result = await session.execute(select(SampleBatch))
        all_batches = result.scalars().all()
        affected_sample_batches = []
        for batch in all_batches:
            build_params = batch.build_params
            if (
                "ion_mechanisms" in build_params
                and ionization_mechanism_id in build_params["ion_mechanisms"]
            ):
                affected_sample_batches.append(
                    {
                        "sample_batch_id": batch.sample_batch_id,
                        "sample_batch_name": batch.sample_batch_name,
                    }
                )

        # Step 4: Return ionization mechanism details with sample batches
        ionization_mechanism_dict = ionization_mechanism.to_dict()
        ionization_mechanism_dict["sample_batches_count"] = len(affected_sample_batches)
        ionization_mechanism_dict["sample_batches"] = affected_sample_batches
        return ionization_mechanism_dict


@api_controller()
async def create_ionization_mechanism(
    ionization_mechanism: IonizationMechanismCreate,
) -> dict:
    """
    Creates a new ionization mechanism and generates corresponding ions for each existing target compound in the database.

    Steps:
    1. Create a new ionization mechanism instance and add it to the session.
    2. Fetch all target compounds from the database.
    3. For each target compound, create target ions with the new ionization mechanism.
    4. Commit the transaction to persist changes to the database.
    5. Return the created ionization mechanism's details.

    :param ionization_mechanism: Ionization mechanism to create
    :type ionization_mechanism: IonizationMechanismCreate
    :raises NotFoundException: If the ionization mechanism is not found after creation.
    :return: Created ionization mechanism details.
    :rtype: dict
    """
    # Step 1: Create a new ionization mechanism instance and add it to the session.
    async with async_session() as session:
        new_ionization_mechanism = IonizationMechanism(
            ionization_mechanism_id=gen_id(11), **ionization_mechanism.model_dump()
        )
        session.add(new_ionization_mechanism)

        # Step 2: Fetch all target compounds
        stmt = select(TargetCompound)
        result = await session.execute(stmt)
        target_compounds = result.scalars().all()

        # Step 3: Create target ions with new mechanism for each compound
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

        # Step 4: Commit the transaction
        await session.commit()
        await session.refresh(new_ionization_mechanism)

    if not new_ionization_mechanism:
        raise NotFoundException(
            f"Ionization mechanism with ID '{new_ionization_mechanism.ionization_mechanism_id}' not found after it should have been created"
        )

    # Step 5: Emit the reload event
    await sio.emit(
        "ionization_mechanism_reload",
        namespace="/",
    )

    # Step 6: Return created ionization mechanism details
    return new_ionization_mechanism.to_dict()


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
        ionization_details = await get_ionization_mechanism(ionization_mechanism_id)
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

    # Step 4: Emit the reload event
    await sio.emit(
        "ionization_mechanism_reload",
        namespace="/",
    )

    return {
        "message": f"Ionization mechanism '{ionization_mechanism.ionization_mechanism}' was deleted successfully."
    }
