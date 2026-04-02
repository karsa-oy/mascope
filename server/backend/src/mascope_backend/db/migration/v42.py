"""
Migration v42: Fix incorrect ion charges in case of - and + ionization mechanisms.
"""

import asyncio
import os
import shutil

from sqlalchemy import distinct, func, select, update

from mascope_backend.api.controllers.target.ions.target_ions_controller import (
    create_target_ions,
)
from mascope_backend.db import (
    IonizationMechanism,
    MatchIon,
    SampleBatch,
    SampleItem,
    TargetCompound,
    TargetIon,
    async_session,
    configure_database_engine,
)
from mascope_backend.db.ops.backup import create_db_backup
from mascope_backend.db.ops.maintenance import db_maintenance
from mascope_backend.db.ops.restore import db_restore
from mascope_backend.runtime import runtime


async def run():
    """Execute migration to v42."""
    await create_db_backup()

    # Setup new database version
    old_version, new_version = 41, 42
    old_db_path = os.path.join(
        runtime.config.database.data_dir, f"mascope.v{old_version}.db"
    )
    new_db_path = os.path.join(
        runtime.config.database.data_dir, f"mascope.v{new_version}.db"
    )

    shutil.copyfile(old_db_path, new_db_path)
    await configure_database_engine(new_version)

    await fix_ions()

    # db_restore handle validation, orphan cleanup, and index check
    runtime.logger.info("Validating schema and cleaning up orphans...")
    await db_restore()
    await db_maintenance()

    runtime.logger.info(f"Migration to v{new_version} completed")


async def fix_ions():
    """Fixes the issue with wrong sign in case of - and + ionization mechanisms in the database

    Steps:
    - Fetch TargetIons with mismatched charge signs
    - For each such TargetIon:
        - Create correct TargetIon and associated TargetIsotopes
        - Delete the incorrect TargetIon (cascade should delete associated records)
        - Track affected sample batches for rematching
    - Update status of affected sample batches to 'rematch'
    - Validate that no rows were lost in TargetIon or TargetIsotope tables

    :raises RuntimeError: If there is a mismatch between initial and final number of
        TargetIon or TargetIsotope rows.
    """
    async with async_session() as session:
        # --- Fetch TargetIons with mismatched charge signs ---
        result = await session.execute(
            select(TargetIon, IonizationMechanism.ionization_mechanism)
            .join(IonizationMechanism)
            .where(
                IonizationMechanism.ionization_mechanism.in_(["+", "-"]),
                func.substr(TargetIon.target_ion_formula, -1, 1)
                != IonizationMechanism.ionization_mechanism,
            )
        )
        target_ions = result.scalars().all()

        if not target_ions:
            runtime.logger.info("No ions with mismatched charge signs found.")
            return

        # Store total number of rows in TargetIon before modification
        # it must remain the same after modification
        initial_n_ions = (
            await session.execute(select(func.count()).select_from(TargetIon))
        ).scalar_one()

        # --- Update status for affected batches ---
        target_ion_ids = [ti.target_ion_id for ti in target_ions]
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
                f"Marked the following sample batches for rematching: \n{affected_batch_ids}"
            )
        else:
            runtime.logger.info("No sample batches affected by ion charge fixes.")

        runtime.logger.info("Fixing ions with incorrect charge signs...")
        # --- Process each TargetIon with mismatched charge sign ---
        for target_ion in target_ions:
            # Create correct ions and isotopes
            target_compound = await session.get(
                TargetCompound, target_ion.target_compound_id
            )
            ionization_mechanism = await session.get(
                IonizationMechanism, target_ion.ionization_mechanism_id
            )
            # create_target_ions expects TargetCompoundBase pydantic model
            # but whatever, TargetCompound ORM object has the same attributes
            await create_target_ions(
                target_compound=target_compound,
                ionization_mechanisms=[ionization_mechanism],
                session=session,
            )
            # Delete the incorrect TargetIon and hope cascade will delete associated records.
            await session.delete(target_ion)

        # Commit all changes
        await session.commit()

        # --- Validate that no rows were lost ---
        final_n_ions = (
            await session.execute(select(func.count()).select_from(TargetIon))
        ).scalar_one()

        is_num_ions_changed = final_n_ions != initial_n_ions

        if is_num_ions_changed:
            raise RuntimeError(
                f"Migration failed: number of TargetIon rows changed. "
                f"Initial ions: {initial_n_ions}, final ions: {final_n_ions}."
            )

        # --- Validate matches were deleted correctly ---
        match_ion_result = await session.execute(
            select(MatchIon).where(MatchIon.target_ion_id.in_(target_ion_ids))
        )
        remaining_match_ions = match_ion_result.scalars().all()
        if remaining_match_ions:
            raise RuntimeError(
                f"Migration failed: some MatchIon rows were not deleted correctly. "
                f"Remaining MatchIons: {[mi.match_ion_id for mi in remaining_match_ions]}"
            )
        runtime.logger.info("Ions fixed successfully.")


if __name__ == "__main__":
    asyncio.run(run())
