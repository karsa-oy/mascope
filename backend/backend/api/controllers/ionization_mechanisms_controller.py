from fastapi import HTTPException
from sqlalchemy import asc, desc, func
from sqlalchemy.future import select
from backend.db import async_session
from backend.db.id import gen_id

from .target_ions_controller import create_target_ions
from ..models.models import IonizationMechanism, TargetCompound
from ..models.pydantic_models.ionization_mechanism_pydantic_model import (
    IonizationMechanismCreate,
)


async def get_ionization_mechanisms(
    ionization_mechanism_polarity: str = None,
    ionization_mechanism: str = None,
    reagent: str = None,
    sort: str = None,
    order: str = None,
    page: int = 0,
    limit: int = 100,
):
    async with async_session() as session:
        stmt = select(IonizationMechanism)

        if ionization_mechanism_polarity:
            stmt = stmt.filter(
                IonizationMechanism.ionization_mechanism_polarity
                == ionization_mechanism_polarity
            )

        if reagent:
            stmt = stmt.filter(IonizationMechanism.reagent == reagent)

        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(IonizationMechanism, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(IonizationMechanism, sort)))

        # Get total count
        count_stmt = select(func.count()).select_from(stmt)
        total = await session.scalar(count_stmt)

        # Get paginated results
        stmt = stmt.offset(page * limit).limit(limit)
        result = await session.execute(stmt)
        ionization_mechanisms = result.scalars().all()

        return {
            "results": total,
            "data": [
                ionization_mechanism.to_dict()
                for ionization_mechanism in ionization_mechanisms
            ],
        }


async def get_ionization_mechanism(ionization_mechanism_id: str):
    async with async_session() as session:
        stmt = select(IonizationMechanism).filter(
            IonizationMechanism.ionization_mechanism_id == ionization_mechanism_id
        )
        result = await session.execute(stmt)
        ionization_mechanism = result.scalars().first()

        if not ionization_mechanism:
            raise HTTPException(
                status_code=404,
                detail=f"IonizationMechanism with ID {ionization_mechanism_id} not found",
            )

        return ionization_mechanism.to_dict()


async def create_ionization_mechanism(
    ionization_mechanism: IonizationMechanismCreate,
) -> dict:
    """Function to create a new ionization mechanism. Generates corresponding ions
    for each existing target compound in the database.

    :param ionization_mechanism: Ionization mechanism to create
    :type ionization_mechanism: IonizationMechanismCreate
    :raises HTTPException: Failed to create the ionization mechanism
    :return: Created ionization mechanism
    :rtype: dict
    """

    async with async_session() as session:
        new_ionization_mechanism = IonizationMechanism(
            ionization_mechanism_id=gen_id(11),
            ionization_mechanism_polarity=ionization_mechanism.ionization_mechanism_polarity,
            ionization_mechanism=ionization_mechanism.ionization_mechanism,
            reagent=ionization_mechanism.reagent,
        )
        session.add(new_ionization_mechanism)

        # Get all target compounds
        stmt = select(TargetCompound)
        result = await session.execute(stmt)
        target_compounds = result.scalars().all()
        for i, target_compound in enumerate(target_compounds):
            # Create target ions with new mechanism for each compound
            try:
                # Try if target compound is given by mass (try to parse composition into float)
                target_compound_mass = float(target_compound.target_compound_formula)
            except ValueError:
                target_compound_mass = None

            await create_target_ions(
                target_compound,
                [new_ionization_mechanism],
                target_compound_mass,
                session=session,
            )

        await session.commit()
        await session.refresh(new_ionization_mechanism)

    if not new_ionization_mechanism:
        raise HTTPException(
            status_code=400,
            detail="Failed to create ionization mechanism",
        )

    return new_ionization_mechanism.to_dict()
