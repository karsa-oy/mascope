"""
Migration script for v32: Data Correction for Faulty Target Compounds.

This migration finds target_compound records with formulas containing parentheses,
removes and recreates them, re-associates them with their collections, and rematches affected batches.
"""

import asyncio
import os
import shutil

from sqlalchemy import select

from mascope_backend.api.controllers.target.compounds.target_compounds_controller import (
    create_target_compound,
    delete_target_compound,
)
from mascope_backend.api.models.target.compounds.target_compound_pydantic_model import (
    TargetCompoundBase,
)

from mascope_backend.db import async_session, configure_database_engine
from mascope_backend.db.ops.backup import create_db_backup

from mascope_backend.db.models import (
    TargetCompound,
    TargetCompoundInTargetCollection,
    TargetCollectionInSampleBatch,
)
from mascope_backend.api.controllers.match.match_controller import rematch_batches
from mascope_backend.api.models.match.match_pydantic_model import (
    RematchBatchesBody,
)
from mascope_backend.runtime import runtime


async def run():
    # Step 1: Create backup before migration
    await create_db_backup()

    # Step 2: Setup new database version
    old_version = 31
    new_version = 32
    old_db_path = os.path.join(runtime.config.database, f"mascope.v{old_version}.db")
    new_db_path = os.path.join(runtime.config.database, f"mascope.v{new_version}.db")

    # Copy database file to new version
    shutil.copyfile(old_db_path, new_db_path)

    # Configure async engine for new version
    await configure_database_engine(new_version)

    # Step 3: Identify and fix faulty target compounds
    async with async_session() as session:
        # 1. Find faulty target_compounds, i.e. formula includes parenthesis
        faulty_compounds = (
            (
                await session.execute(
                    select(TargetCompound).where(
                        (
                            TargetCompound.target_compound_formula.like("%(%")
                            | TargetCompound.target_compound_formula.like("%)%")
                        )
                    )
                )
            )
            .scalars()
            .all()
        )

        if not faulty_compounds:
            runtime.logger.info("No faulty target_compounds found. Migration complete.")
            return

        faulty_ids = [tc.target_compound_id for tc in faulty_compounds]
        runtime.logger.info(
            f"Found {len(faulty_ids)} faulty target_compounds: {faulty_ids}"
        )

        # 2. Find target collections containing these compounds, to be updated with corrected compounds
        tc_in_collections = (
            (
                await session.execute(
                    select(TargetCompoundInTargetCollection).where(
                        TargetCompoundInTargetCollection.target_compound_id.in_(
                            faulty_ids
                        )
                    )
                )
            )
            .scalars()
            .all()
        )
        collection_ids = list({tc.target_collection_id for tc in tc_in_collections})

        runtime.logger.info(
            f"Found {len(collection_ids)} affected target_collections: {collection_ids}"
        )

        # 3. Find sample batches associated with those collections, to be rematched
        batch_links = (
            (
                await session.execute(
                    select(TargetCollectionInSampleBatch).where(
                        TargetCollectionInSampleBatch.target_collection_id.in_(
                            collection_ids
                        )
                    )
                )
            )
            .scalars()
            .all()
        )
        batch_ids = list({bl.sample_batch_id for bl in batch_links})

        runtime.logger.info(
            f"Found {len(batch_ids)} affected sample_batches: {batch_ids}"
        )

        # 4. Delete faulty target compounds, and associated ions etc. (cascade delete)
        for tc in faulty_compounds:
            await delete_target_compound(
                tc.target_compound_id, independent_transaction=True
            )
        runtime.logger.info("Deleted faulty target_compounds.")

        # 5. Recreate target compounds, and associated ions etc.
        recreated_ids = []
        faulty_to_new_map = {}
        for tc in faulty_compounds:
            new_tc = TargetCompoundBase(
                target_compound_name=tc.target_compound_name,
                target_compound_formula=tc.target_compound_formula,
                cas_number=tc.cas_number,
            )
            recreated_ids.append(tc.target_compound_id)
            created_compound_data = await create_target_compound(
                [new_tc], independent_transaction=True
            )
            new_target_compound_id = created_compound_data["target_compound_ids"][0]
            faulty_to_new_map[tc.target_compound_id] = new_target_compound_id
            runtime.logger.info(f"Recreated target_compound: {new_target_compound_id}")

        # 6. Re-associate newly created compounds with the collections
        for tcic in tc_in_collections:
            runtime.logger.info(
                f"Re-associating target_compound previously known as {tcic.target_compound_id} "
                f"into a new record {faulty_to_new_map[tcic.target_compound_id]} "
                f"with target_collection {tcic.target_collection_id}"
            )
            session.add(
                TargetCompoundInTargetCollection(
                    target_compound_id=faulty_to_new_map[tcic.target_compound_id],
                    target_collection_id=tcic.target_collection_id,
                )
            )
        await session.commit()
        runtime.logger.info("Re-associated target compounds with target collections.")

        # 7. Database changes completed. Rematch affected sample batches
        if batch_ids:
            rematch_batches_body = RematchBatchesBody(
                sample_batch_ids=[bid for bid in batch_ids]
            )
            try:
                await rematch_batches(
                    rematch_batches_body,
                    independent_transaction=True,
                    sid="",
                    process_id="",
                )
                runtime.logger.info("Rematching completed successfully")
            except Exception as e:
                runtime.logger.error(f"Rematching failed with error: {str(e)}")
                runtime.logger.warning(
                    "Migration will continue, but manual rematching may be required"
                )
    runtime.logger.info("v32 migration completed.")


if __name__ == "__main__":
    asyncio.run(run())
