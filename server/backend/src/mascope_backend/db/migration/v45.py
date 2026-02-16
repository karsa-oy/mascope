"""
Migration v45: Fix isotope data for ions containing isotopically labelled elements (^N).

The previous isotope prediction logic had a bug where custom elements (like ^N) were
not handled correctly, resulting in:
- Incorrect m/z values
- Incorrect relative abundances
- Malformed isotope formulae

This migration:
- Finds all TargetIons with ^N in their formula
- Recalculates isotopes for those ions using the corrected prediction logic
- Deletes old isotopes and inserts the corrected ones
- Marks affected sample batches for rematching
"""

import asyncio
import os
import shutil
from tqdm import tqdm

from sqlalchemy import select, update, delete, distinct

from mascope_molmass import Formula

from mascope_backend.api.controllers.target.lib.compute.target_ions_compute import (
    _get_raw_ion,
    group_target_isotopes,
    predict_isotopes,
    RESOLUTION_LOW,
)
from mascope_backend.db import (
    TargetIon,
    TargetIsotope,
    IonizationMechanism,
    TargetCompound,
    SampleItem,
    SampleBatch,
    MatchIon,
    async_session,
    configure_database_engine,
)
from mascope_backend.db.id import gen_id
from mascope_backend.db.ops.backup import create_db_backup
from mascope_backend.db.ops.maintenance import db_maintenance
from mascope_backend.db.ops.restore import db_restore
from mascope_backend.runtime import runtime


async def run():
    """Execute migration to v45."""
    await create_db_backup()

    # Setup new database version
    old_version, new_version = 44, 45
    old_db_path = os.path.join(runtime.config.database, f"mascope.v{old_version}.db")
    new_db_path = os.path.join(runtime.config.database, f"mascope.v{new_version}.db")

    shutil.copyfile(old_db_path, new_db_path)
    await configure_database_engine(new_version)

    await fix_custom_element_isotopes()

    # db_restore handles validation, orphan cleanup, and index check
    runtime.logger.info("Validating schema and cleaning up orphans...")
    await db_restore()
    await db_maintenance()

    runtime.logger.info(f"Migration to v{new_version} completed")


async def fix_custom_element_isotopes():
    """Fix isotope data for ions containing custom elements (^N).

    Steps:
    - Fetch TargetIons containing ^N in their formula
    - For each such ion:
        - Get the associated TargetCompound and IonizationMechanism
        - Recalculate isotopes using corrected prediction logic
        - Delete old TargetIsotopes for this ion
        - Insert new TargetIsotopes with correct data
    - Mark affected sample batches for rematching
    """
    async with async_session() as session:
        # --- Fetch TargetIons containing ^N ---
        result = await session.execute(
            select(TargetIon).where(TargetIon.target_ion_formula.contains("^N"))
        )
        target_ions = result.scalars().all()

        if not target_ions:
            runtime.logger.info("No ions with custom elements (^N) found.")
            return

        runtime.logger.info(
            f"Found {len(target_ions)} ions with custom elements. Fixing isotopes..."
        )

        # Collect target ion IDs for batch status update
        target_ion_ids = [ti.target_ion_id for ti in target_ions]

        # --- Mark affected batches for rematch ---
        await mark_affected_batches_for_rematch(session, target_ion_ids)

        # --- Process each ion ---
        for target_ion in tqdm(target_ions, desc="Fixing isotopes", unit="ion"):
            await fix_ion_isotopes(session, target_ion)

        await session.commit()

        runtime.logger.info(
            f"Fixed isotopes for {len(target_ions)} ions with custom elements."
        )


async def mark_affected_batches_for_rematch(session, target_ion_ids: list[str]):
    """Mark sample batches containing samples matched to the given ions for rematching.

    :param session: Database session
    :param target_ion_ids: List of target ion IDs whose isotopes are being fixed
    """
    batch_result = await session.execute(
        select(distinct(SampleBatch.sample_batch_id))
        .join(SampleItem, SampleBatch.sample_batch_id == SampleItem.sample_batch_id)
        .join(MatchIon, SampleItem.sample_item_id == MatchIon.sample_item_id)
        .where(MatchIon.target_ion_id.in_(target_ion_ids))
    )
    affected_batch_ids = set(batch_result.scalars().all())

    if affected_batch_ids:
        await session.execute(
            update(SampleBatch)
            .where(SampleBatch.sample_batch_id.in_(affected_batch_ids))
            .values(status="rematch")
        )
        runtime.logger.info(
            f"Marked {len(affected_batch_ids)} sample batches for rematching."
        )
    else:
        runtime.logger.info("No sample batches affected by isotope fixes.")


async def fix_ion_isotopes(session, target_ion: TargetIon):
    """Recalculate and replace isotopes for a single target ion.

    :param session: Database session
    :param target_ion: The TargetIon to fix isotopes for
    """
    # Get associated compound and ionization mechanism
    target_compound = await session.get(TargetCompound, target_ion.target_compound_id)
    ionization_mechanism = await session.get(
        IonizationMechanism, target_ion.ionization_mechanism_id
    )

    if not target_compound or not ionization_mechanism:
        runtime.logger.warning(
            f"Skipping ion {target_ion.target_ion_id}: missing compound or mechanism"
        )
        return

    # --- Delete old isotopes for this ion ---
    await session.execute(
        delete(TargetIsotope).where(
            TargetIsotope.target_ion_id == target_ion.target_ion_id
        )
    )

    # --- Recalculate isotopes ---
    ion_formula = target_ion.target_ion_formula[:-1]  # Remove charge (+/-)
    compound_formula = Formula(target_compound.target_compound_formula)
    raw_ion = _get_raw_ion(ionization_mechanism.ionization_mechanism, compound_formula)

    # Predict high resolution isotopes
    high_res_isotopes = predict_isotopes(raw_ion, ion_formula)
    # Group for low resolution
    low_res_isotopes = group_target_isotopes(*high_res_isotopes, RESOLUTION_LOW)

    # --- Insert new isotopes ---
    new_isotopes = []
    for resolution, (masses, probs, formulae) in [
        ("HIGH", high_res_isotopes),
        ("LOW", low_res_isotopes),
    ]:
        for mz, rel_abu, formula in zip(masses, probs, formulae):
            new_isotopes.append(
                TargetIsotope(
                    target_isotope_id=gen_id(16),
                    target_ion_id=target_ion.target_ion_id,
                    mz=mz,
                    relative_abundance=rel_abu,
                    resolution=resolution,
                    target_isotope_formula=formula,
                )
            )

    session.add_all(new_isotopes)


if __name__ == "__main__":
    asyncio.run(run())
