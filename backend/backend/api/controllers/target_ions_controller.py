from fastapi import HTTPException
from sqlalchemy import asc, desc, func, select
from typing import List

from backend.db import async_session
from backend.api_sio import sio
from backend.db.id import gen_id

from lib.molmass import Formula

from ..models.models import (
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
from ..models.pydantic_models.target_compound_pydantic_model import TargetCompoundBase
from ..models.pydantic_models.target_ion_pydantic_model import TargetIonUpdate


async def get_target_ions(
    target_compound_id: str,
    ionization_mechanism_id: str,
    target_ion_formula: str,
    sort: str,
    order: str,
    page: int,
    limit: int,
):
    async with async_session() as session:
        stmt = select(TargetIon)

        if target_compound_id:
            stmt = stmt.filter(TargetIon.target_compound_id == target_compound_id)

        if ionization_mechanism_id:
            stmt = stmt.filter(
                TargetIon.ionization_mechanism_id == ionization_mechanism_id
            )

        if target_ion_formula:
            stmt = stmt.filter(TargetIon.target_ion_formula == target_ion_formula)

        if sort:
            if order == "desc":
                stmt = stmt.order_by(desc(getattr(TargetIon, sort)))
            else:
                stmt = stmt.order_by(asc(getattr(TargetIon, sort)))

        # Get total count
        count_stmt = select(func.count()).select_from(stmt)
        total = await session.scalar(count_stmt)

        # Get paginated results
        stmt = stmt.offset(page * limit).limit(limit)
        result = await session.execute(stmt)
        target_ions = result.scalars().all()

        return {
            "results": total,
            "data": [target_ion.to_dict() for target_ion in target_ions],
        }


async def get_target_ion(target_ion_id: str):
    async with async_session() as session:
        stmt = select(TargetIon)

        if target_ion_id:
            stmt = stmt.filter(TargetIon.target_ion_id == target_ion_id)

        result = await session.execute(stmt)
        target_ion = result.scalars().first()

        if not target_ion:
            raise HTTPException(status_code=404, detail=f"Target ion not found")

        return target_ion.to_dict()


async def create_target_ions(
    target_compound: TargetCompoundBase,
    ionization_mechanisms: List[IonizationMechanism],
    target_compound_mass: float = None,
    session=None,
) -> dict:
    """Function to create target ion and target isotope records
    derived from a given target compound and list of ionization mechanisms to apply.
    If target compound mass is given, it will be used instead of compound formula.

    :param target_compound: Target compound to derive ions and isotopes from
    :type target_compound: TargetCompoundBase
    :param ionization_mechanisms: List of ionization mechanisms to apply to the compound
    :type ionization_mechanisms: List[IonizationMechanism]
    :param target_compound_mass: Mass of the target compound (if formula is not known),
    defaults to None. If None, formula will be used.
    :type target_compound_mass: float, optional
    :param session: Database session, if not given makes an independent transaction, defaults to None
    :type session: SQLAlchemy.AsyncSession, optional
    :return: Return created target ions and isotopes, and message log
    :rtype: dict
    """
    independent_transaction = False

    if session is None:
        independent_transaction = True
        session = async_session()

    # Helper functions
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
                print("Failed to parse ion formula: %s" % e)  # TODO: Catch the error
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
                raw_isotopes = [(-raw_ion.mz, 1.0)]

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

    # Initialize message log
    message_log = {}  # TODO: Populate with information

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

    return {
        "created_ions": target_ions,
        "created_isotopes": target_isotopes,
        "message_logs": message_log,
    }


async def update_target_ion(target_ion_id: str, target_ion_update: TargetIonUpdate):
    async with async_session() as session:
        target_ion = await session.get(TargetIon, target_ion_id)
        if not target_ion:
            raise HTTPException(
                status_code=404,
                detail=f"Target ion with ID {target_ion_id} not found",
            )

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
