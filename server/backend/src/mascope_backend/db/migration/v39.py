"""
Migration script for v39: replace integer sample_peak_id with a peak ID
from the sample file
"""

import asyncio
import os
import shutil
from tqdm import tqdm
import contextlib
from sqlalchemy import select, text

from mascope_backend.db import async_session, configure_database_engine
from mascope_backend.db.ops.backup import create_db_backup
from mascope_backend.db.models import MatchIsotope, SampleItem

import mascope_file.io as m_io

from mascope_backend.runtime import runtime


@contextlib.contextmanager
def suppress_logger(loguru_logger):
    """
    Context manager to completely suppress all logging output from the logger.
    """
    loguru_logger.disable("")
    try:
        yield
    finally:
        loguru_logger.enable("")


async def run():
    # Create backup before migration
    await create_db_backup()

    # Setup new database version
    old_version = 38
    new_version = 39
    old_db_path = os.path.join(runtime.config.database, f"mascope.v{old_version}.db")
    new_db_path = os.path.join(runtime.config.database, f"mascope.v{new_version}.db")

    # Copy database file to new version
    shutil.copyfile(old_db_path, new_db_path)

    await configure_database_engine(new_version)

    # --- Collect all MatchIsotope entries and associated SampleItems ---
    match_isotopes = await collect_match_isotopes()
    sample_items = await collect_unique_sample_items(match_isotopes)

    # --- Process each MatchIsotope to update sample_peak_id ---
    updated_match_isotopes = []
    with suppress_logger(runtime.logger):
        for match_isotope in tqdm(
            match_isotopes,
            desc="Fill in sample_peak_id in DB with string IDs...",
        ):
            updated_match_isotope = await process_match_isotope(
                match_isotope, sample_items
            )
            if updated_match_isotope:
                # Recreate MatchIsotope instance to avoid SQLAlchemy state issues
                updated_match_isotope = MatchIsotope(**updated_match_isotope.to_dict())
                updated_match_isotopes.append(updated_match_isotope)

    # --- Re-create match_isotope table with updated entries ---
    await re_create_match_isotope_table(updated_match_isotopes)


async def collect_match_isotopes():
    """Collect all MatchIsotope entries from the database."""
    async with async_session() as session:
        stmt = select(MatchIsotope)
        result = await session.execute(stmt)
        match_isotopes = result.scalars().all()

    return match_isotopes


async def collect_unique_sample_items(
    match_isotopes: list[MatchIsotope],
) -> dict[str, SampleItem]:
    """Collect unique SampleItem entries associated with the given MatchIsotopes."""
    async with async_session() as session:
        sample_item_ids = list(set([mi.sample_item_id for mi in match_isotopes]))
        stmt = select(SampleItem).where(SampleItem.sample_item_id.in_(sample_item_ids))
        result = await session.execute(stmt)
        sample_items = result.scalars().all()
        sample_items = {si.sample_item_id: si for si in sample_items}

    return sample_items


async def process_match_isotope(
    match_isotope: MatchIsotope, sample_items: dict[str, SampleItem]
) -> MatchIsotope | None:
    """Process a single MatchIsotope to update its sample_peak_id.
    -1 indicates no peak matched; set to empty string.
    If sample item not found or unexpected error occurs, return None to indicate deletion.
    """
    if match_isotope.sample_peak_id == -1:
        # No peak matched; set to empty string
        match_isotope.sample_peak_id = ""
        return match_isotope

    sample_item = sample_items.get(match_isotope.sample_item_id)
    if not sample_item:
        tqdm.write(
            f"Sample item with ID '{match_isotope.sample_item_id}' not found. "
            f"Match isotope {match_isotope.target_isotope_id} will be deleted."
        )
        return None

    try:
        filename = sample_item.filename
        peak_data = m_io.load_file(filename, vars=["peak_timeseries"])
        peak_ids = peak_data.id.values
        sample_peak_id = peak_ids[match_isotope.sample_peak_id]
        match_isotope.sample_peak_id = sample_peak_id
        return match_isotope
    except Exception as e:
        tqdm.write(
            f"Error processing match isotope {match_isotope.target_isotope_id}: "
            f"{type(e).__name__}: {e}. "
            "Entry will be deleted."
        )
        return None


async def re_create_match_isotope_table(updated_match_isotopes: list[MatchIsotope]):
    """Re-create the match_isotope table with updated entries."""
    async with async_session() as session:
        # Drop existing match_isotope table
        delete_query = text("DROP TABLE IF EXISTS match_isotope")
        await session.execute(delete_query)

        # Re-create match_isotope table
        connection = await session.connection()
        await connection.run_sync(MatchIsotope.__table__.create)

        # Insert updated entries
        session.add_all(updated_match_isotopes)
        await session.commit()


if __name__ == "__main__":
    asyncio.run(run())
