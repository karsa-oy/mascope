import os
import shutil
import asyncio

from sqlalchemy import text, select
from IsoSpecPy import IsoThreshold

from mascope_backend.api.controllers.match.match_controller import (
    rematch_batches,
)
from mascope_backend.api.models.match.match_pydantic_model import (
    RematchBatchesBody,
    RematchBatchBody,
)
from mascope_molmass import Formula
from mascope_molmass.elements import ELECTRON


from mascope_backend.db.models import (
    IonizationMechanism,
    SampleBatch,
    TargetIon,
    TargetIsotope,
)
from mascope_backend.db import configure_database_engine, async_session
from mascope_backend.db.id import gen_id
from mascope_backend.db.ops.backup import create_db_backup

from mascope_backend.runtime import runtime


async def run():
    # Create a backup before migration
    await create_db_backup()

    # Setup new database version
    new_version = 19
    old_db_path = os.path.join(runtime.config.database, "mascope.v18.db")
    new_db_path = os.path.join(runtime.config.database, f"mascope.v{new_version}.db")

    # Create a copy of the old database for the new migration
    shutil.copyfile(old_db_path, new_db_path)

    # Update the engine to the new database (also updates global async_session)
    await configure_database_engine(new_version)

    runtime.logger.info("Adding resolution column to the target_isotope table.")

    async with async_session() as session:
        await session.execute(
            text(
                "ALTER TABLE target_isotope ADD COLUMN resolution VARCHAR(8) NOT NULL DEFAULT 'LOW';"
            )
        )
        await session.commit()

    # Read all ion formulae
    runtime.logger.info("Reading existing target ions.")
    async with async_session() as session:
        stmt = select(TargetIon)
        result = await session.execute(stmt)
        target_ions = result.scalars().all()

    runtime.logger.info("Calculating high resolution isotopes.")

    # Init high resolution target isotopes list
    target_isotopes = []
    for ion in target_ions:
        try:
            # Branch if ion created based on mass, not formula (adapted from "generate_target_ions_from_mass")
            if "." in ion.target_ion_formula:
                # Strip ionization to parse mass
                target_mass = float(ion.target_ion_formula.split("-")[0].split("+")[0])
                # Fetch ionization mechanism from db
                async with async_session() as session:
                    stmt = select(IonizationMechanism).where(
                        IonizationMechanism.ionization_mechanism_id
                        == ion.ionization_mechanism_id
                    )
                    result = await session.execute(stmt)
                    ionization_mechanism = result.scalars().first()
                mechanism = ionization_mechanism.ionization_mechanism
                # Parse ionization mechanism
                if len(mechanism) > 1:
                    # Addition or abstraction mechanism
                    # Calculate isotopic pattern of the ionization mechanism
                    mechanism_formula = Formula(
                        "(" + mechanism[1:-1] + ")" + mechanism[-1]
                    )
                    is_adduct = mechanism[0] == "+"
                    if is_adduct:
                        # Addition mechanism
                        predicted_peaks = IsoThreshold(
                            formula=mechanism_formula.formula, threshold=0.01
                        )
                        masses = [
                            (
                                target_mass
                                + float(m)
                                - ELECTRON.mass * mechanism_formula.charge
                            )
                            / abs(mechanism_formula.charge)
                            for m in predicted_peaks.masses
                        ]
                        probs = [float(p) for p in predicted_peaks.probs]
                    else:
                        # Abstraction mechanism, no knowledge of the isotopic pattern
                        masses = [target_mass - mechanism_formula.mass]
                        probs = [1.0]
                else:
                    # Special case: electron transfer
                    is_addition = mechanism[0] == "-"
                    masses = [
                        (
                            target_mass + ELECTRON.mass
                            if is_addition
                            else target_mass - ELECTRON.mass
                        )
                    ]
                    probs = [1.0]
            # Branch if ion created based on formula
            else:
                # Split base and charge
                target_ion = Formula(ion.target_ion_formula)

                # Predict peaks, take those with r.a.>1%
                predicted_peaks = IsoThreshold(
                    formula=target_ion.formula, threshold=0.01
                )

                # Extract resolution masses and probabilities, correct masses for the electron charge
                masses = [
                    (float(m) - ELECTRON.mass * target_ion.charge)
                    / abs(target_ion.charge)
                    for m in predicted_peaks.masses
                ]
                probs = [float(p) for p in predicted_peaks.probs]

        except Exception as e:
            runtime.logger.error(
                f"Error calculating isotopes for target ion {ion}: {e}"
            )
            continue

        # Store high resolution isotopes
        target_isotopes.extend(
            [
                TargetIsotope(
                    target_isotope_id=gen_id(16),
                    target_ion_id=ion.target_ion_id,
                    mz=mz,
                    relative_abundance=rel_abu,
                    resolution="HIGH",
                )
                for mz, rel_abu in zip(masses, probs)
            ]
        )

    runtime.logger.info("Writing high resolution isotopes to the database.")

    async with async_session() as session:
        for target_isotope in target_isotopes:
            # Add the isotopes to be committed to the db
            session.add(target_isotope)
        await session.commit()

    # Get all sample batches
    async with async_session() as session:
        stmt = select(SampleBatch)
        result = await session.execute(stmt)
        sample_batch_list = result.scalars().all()

    runtime.logger.info(f"Rematching {len(sample_batch_list)} sample batches.")

    sample_batch_ids = [
        sample_batch.sample_batch_id for sample_batch in sample_batch_list
    ]
    rematch_batch_bodies = [
        RematchBatchBody(sample_batch_id=sample_batch_id)
        for sample_batch_id in sample_batch_ids
    ]
    rematch_batches_body = RematchBatchesBody(sample_batches=rematch_batch_bodies)

    await rematch_batches(
        rematch_batches_body, independent_transaction=True, sid="", process_id=""
    )


if __name__ == "__main__":
    asyncio.run(run())
