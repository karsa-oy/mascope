from sqlalchemy import asc, desc, func
from sqlalchemy.future import select
from backend.db.id import gen_id
from backend.db_api_rest import async_session
from ..utils.api_features import api_controller
from ..exceptions import NotFoundException
from .target_ions_controller import create_target_ions
from ..models.models import IonizationMechanism, TargetCompound
from ..models.pydantic_models.ionization_mechanism_pydantic_model import (
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
        total = await session.scalar(select(func.count()).select_from(stmt))
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

        # Step 3: Return ionization mechanism details
        return ionization_mechanism.to_dict()


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
            ionization_mechanism_id=gen_id(11), **ionization_mechanism.dict()
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

    # Step 5: Return created ionization mechanism details
    return new_ionization_mechanism.to_dict()
