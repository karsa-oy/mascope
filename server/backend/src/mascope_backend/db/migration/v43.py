"""
Migration v43: Update target_isotope table and rematch affected samples
Changes from v42 to v43:
- Add target_isotope.target_isotope_formula column
- Recompute isotopes for all target ions using updated prediction logic
- Identify ions with significant isotope m/z deviations and rematch associated samples
"""

import asyncio
import os
import shutil
from tqdm import tqdm

from sqlalchemy import text, select
from sqlalchemy.schema import CreateTable
import polars as pl
import numpy as np

from mascope_molmass import Formula

from mascope_backend.api.controllers.target.lib.compute.target_ions_compute import (
    _get_raw_ion,
    group_target_isotopes,
    predict_isotopes,
    RESOLUTION_LOW,
)
from mascope_backend.api.controllers.match.match_controller import rematch_samples
from mascope_backend.db import (
    TargetIsotope,
    MatchIon,
    Sample,
    async_session,
    configure_database_engine,
)
from mascope_backend.db.id import gen_id
from mascope_backend.db.ops.backup import create_db_backup
from mascope_backend.db.ops.maintenance import db_maintenance
from mascope_backend.db.ops.restore import db_restore
from mascope_backend.runtime import runtime


# Precision for exact comparison of high resolution isotopes, DB vs predicted:
DECIMAL_PLACES = 10
# How much the stored in the DB isotopes can deviate from the predicted for low resolution:
LOW_PPM_THRESHOLD = 5.0  # ppm
DEFAULT_MIN_ISOTOPE_ABUNDANCE = 0.1


async def run():
    """Execute migration to v43."""
    await create_db_backup()

    # Setup new database version
    old_version, new_version = 42, 43
    old_db_path = os.path.join(
        runtime.config.database.data_dir, f"mascope.v{old_version}.db"
    )
    new_db_path = os.path.join(
        runtime.config.database.data_dir, f"mascope.v{new_version}.db"
    )

    shutil.copyfile(old_db_path, new_db_path)
    await configure_database_engine(new_version)

    # Disable FK enforcement during migration
    async with async_session() as session:
        await session.execute(text("PRAGMA foreign_keys = OFF;"))

    runtime.logger.info("Applying schema transformations and data updates...")
    await migrate()
    runtime.logger.info("Schema transformations and data updates applied.")

    # Re-enable FK enforcement
    async with async_session() as session:
        await session.execute(text("PRAGMA foreign_keys = ON;"))

    # db_restore handle validation, orphan cleanup, and index check
    runtime.logger.info("Validating schema and cleaning up orphans...")
    await db_restore()
    await db_maintenance()

    runtime.logger.info(f"Migration to v{new_version} completed")


async def migrate():
    """Apply schema transformations and data updates for v43 migration."""
    updated_isotopes_all, ion_rematch_samples_all = await handle_ion_group_updates()
    runtime.logger.info(
        f"Updating target_isotope table with {len(updated_isotopes_all)} isotopes..."
    )
    async with async_session() as session:
        # Drop existing target_isotope table
        await session.execute(text("DROP TABLE target_isotope;"))

        # Recreate target_isotope table from the list of TargetIsotope objects
        create_table_sql = str(
            CreateTable(TargetIsotope.__table__).compile(session.bind)
        )
        await session.execute(text(create_table_sql))
        # Bulk insert updated isotopes
        session.add_all(updated_isotopes_all)

        # Save changes
        await session.commit()

    runtime.logger.info(
        "target_isotope table updated. Rematching affected samples if necessary..."
    )
    # Rematch samples associated with ions whose isotopes above matching threshold changed
    # their m/z values too much
    await rematch_affected_samples(ion_rematch_samples_all)


async def handle_ion_group_updates() -> (
    tuple[list[TargetIsotope], dict[str, list[str]]]
):
    """Provides the list of updated isotopes and the list of ions
    that triggers batch status change to 'rematch'

    :return: Tuple of:
            - List of updated TargetIsotope objects
            - Dictionary of target ion IDs to rematch associated samples
    :rtype: tuple[list[TargetIsotope], dict[str, list[str]]]
    """
    ion_groups = await fetch_ion_groups()
    updated_isotopes_all: list[TargetIsotope] = []
    ion_rematch_samples_all: dict[str, list[str]] = {"HIGH": [], "LOW": []}
    ion_groups_list = list(ion_groups)
    for (ion_id,), ion_group in tqdm(
        ion_groups_list, desc="Processing ions", unit="ion"
    ):
        updated_isotopes, ion_rematch_batch = process_ion_group(ion_id, ion_group)
        updated_isotopes_all.extend(updated_isotopes)
        ion_rematch_samples_all["HIGH"].extend(ion_rematch_batch["HIGH"])
        ion_rematch_samples_all["LOW"].extend(ion_rematch_batch["LOW"])
    return updated_isotopes_all, ion_rematch_samples_all


async def rematch_affected_samples(ion_rematch_samples: dict[str, list[str]]):
    """Rematches provided samples, affected by ion isotope updates.

    :param ion_rematch_samples: Samples to be rematched
    :type ion_rematch_samples: dict[str, list[str]]
    """
    # --- Fetch samples associated with the ions to be rematched ---
    async with async_session() as session:
        high_result = await session.execute(
            select(Sample)
            .select_from(Sample)
            .join(MatchIon, Sample.sample_item_id == MatchIon.sample_item_id)
            .where(MatchIon.target_ion_id.in_(ion_rematch_samples["HIGH"]))
            .where(Sample.instrument.ilike("%orbi%"))
        )
        high_result = high_result.scalars().all()

        low_result = await session.execute(
            select(Sample)
            .select_from(Sample)
            .join(MatchIon, Sample.sample_item_id == MatchIon.sample_item_id)
            .where(MatchIon.target_ion_id.in_(ion_rematch_samples["LOW"]))
            .where(~Sample.instrument.ilike("%orbi%"))  # some TOFs can be APIs
        )
        low_result = low_result.scalars().all()

    high_result = np.unique([i.sample_item_id for i in high_result])
    low_result = np.unique([i.sample_item_id for i in low_result])

    # --- Schedule rematching ---
    if high_result.size > 0:
        runtime.logger.warning(
            f"Scheduling {high_result.size} samples for rematching "
            "(high resolution isotopes do not match by m/z)..."
        )
        await rematch_samples(sample_item_ids=high_result.tolist(), full_remove=True)

    if low_result.size > 0:
        runtime.logger.warning(
            f"Scheduling {low_result.size} samples for rematching "
            f"(low resolution isotope positions deviate by more than {LOW_PPM_THRESHOLD} ppm)..."
        )
        await rematch_samples(sample_item_ids=low_result.tolist(), full_remove=True)


async def fetch_ion_groups() -> pl.dataframe.group_by.GroupBy:
    """Fetch target isotopes joined with target ion, ionization mechanism,
    and target compound data, grouped by target ion ID.

    :return: Grouped target isotopes by target ion ID
    :rtype: pl.dataframe.group_by.GroupBy
    """
    async with async_session() as session:
        result = await session.execute(
            text(
                """
                SELECT
                target_isotope.*,
                target_ion.target_ion_formula,
                ionization_mechanism.ionization_mechanism,
                target_compound.target_compound_formula
                
                FROM target_isotope
                
                JOIN target_ion
                ON target_isotope.target_ion_id = target_ion.target_ion_id
                
                JOIN ionization_mechanism
                ON target_ion.ionization_mechanism_id = ionization_mechanism.ionization_mechanism_id
                
                JOIN target_compound
                ON target_ion.target_compound_id = target_compound.target_compound_id"""
            )
        )
        isotopes = pl.DataFrame(result.fetchall(), schema=result.keys())
        ion_groups = isotopes.group_by("target_ion_id")

    return ion_groups


def process_ion_group(
    ion_id: str, ion_group: pl.dataframe
) -> tuple[list[TargetIsotope], dict[str, list[str]]]:
    """Process a group of isotopes for a given target ion:
    - Predict isotopes with new abundance threshold
    - Compare predicted isotopes with those in the database
    - Determine which isotopes to update and which ions trigger rematch batch status

    :param ion_id: String ID of the target ion
    :type ion_id: str
    :param ion_group: Ion group with associated isotopes from the database
    :type ion_group: pl.dataframe
    :return: List of TargetIsotope objects to update, dictionary of target ion IDs to rematch
            associated samples
    :rtype: tuple[list[TargetIsotope], dict[str, list[str]]]
    """
    updated_isotopes: list[TargetIsotope] = []
    ion_rematch_samples: dict[str, list[str]] = {"HIGH": [], "LOW": []}

    # --- Get raw ion formula and ion string ---
    ion_formula = ion_group["target_ion_formula"][0][:-1]  # remove charge
    ionization_mechanism = ion_group["ionization_mechanism"][0]
    compound_formula_str = ion_group["target_compound_formula"][0]

    if compound_formula_str.replace(".", "", 1).isdigit():
        # Special case: isotopes were generated from mass, keep old values
        for row in ion_group.iter_rows(named=True):
            updated_isotopes.append(
                TargetIsotope(
                    target_ion_id=ion_id,
                    target_isotope_id=row["target_isotope_id"],
                    mz=row["mz"],
                    relative_abundance=row["relative_abundance"],
                    resolution=row["resolution"],
                    target_isotope_formula=f"{row['mz']:.4f}{ionization_mechanism}",
                )
            )
        return updated_isotopes, ion_rematch_samples

    target_compound_formula = Formula(compound_formula_str)
    raw_ion = _get_raw_ion(ionization_mechanism, target_compound_formula)

    # --- Predict isotopes with a new abundance threshold ---
    high_res_predicted_iso = predict_isotopes(raw_ion, ion_formula)
    # Aggregated isotopes for lower resolution
    low_res_predicted_iso = group_target_isotopes(
        *high_res_predicted_iso, RESOLUTION_LOW
    )

    # --- Process high resolution isotopes ---
    high_isotopes, rematch_high = process_resolution(
        ion_id, ion_group, high_res_predicted_iso, "HIGH"
    )
    if rematch_high:
        ion_rematch_samples["HIGH"].append(rematch_high)
    updated_isotopes.extend(high_isotopes)

    # --- Process low resolution isotopes ---
    low_isotopes, rematch_low = process_resolution(
        ion_id, ion_group, low_res_predicted_iso, "LOW"
    )
    if rematch_low:
        ion_rematch_samples["LOW"].append(rematch_low)
    updated_isotopes.extend(low_isotopes)

    return updated_isotopes, ion_rematch_samples


def process_resolution(
    ion_id: str, ion_group: pl.dataframe, predicted_isotopes: tuple, resolution: str
) -> tuple[list[TargetIsotope], str]:
    """Compares isotope m/z values above DEFAULT_MIN_ISOTOPE_ABUNDANCE from
    the database with predicted values:
    - If not all values DB are present in the predicted values, something is off
        related samples will be scheduled for rematching, isotopes are re-written
    - If all values are present, return the isotopes as TargetIsotope objects, keeping their IDs
        to keep matches. The isotopes with with abundance < DEFAULT_MIN_ISOTOPE_ABUNDANCE are
        added to DB from predicted values

    :param ion_id: String ID of the target ion
    :type ion_id: str
    :param ion_group: Ion group with associated isotopes from the database
    :type ion_group: pl.dataframe
    :param predicted_isotopes: Predicted isotopes (masses, abundances, formulas)
    :type predicted_isotopes: tuple
    :param resolution: Resolution string ("HIGH" or "LOW")
    :type resolution: str
    :return: A tuple with:
            - List of TargetIsotope objects
            - Target ion ID for which samples need rematching
    :rtype: tuple[list[TargetIsotope], str]
    """
    # Unpack predicted isotopes and convert to arrays
    masses, abundances, formulas = (
        np.array(predicted_isotopes[0]),
        np.array(predicted_isotopes[1]),
        np.array(predicted_isotopes[2]),
    )
    # Fill in updated target isotopes list with target isotopes of
    # abundance < DEFAULT_MIN_ISOTOPE_ABUNDANCE from predicted
    abundance_mask = abundances < DEFAULT_MIN_ISOTOPE_ABUNDANCE
    target_isotopes = [
        TargetIsotope(
            target_ion_id=ion_id,
            target_isotope_id=gen_id(16),
            mz=mz,
            relative_abundance=ra,
            resolution=resolution,
            target_isotope_formula=form,
        )
        for mz, ra, form in zip(
            masses[abundance_mask], abundances[abundance_mask], formulas[abundance_mask]
        )
    ]
    # Filter ion group for chosen resolution isotopes and abundance >= matching threshold
    ion_group_filt = ion_group.filter(
        (ion_group["resolution"] == resolution)
        & (ion_group["relative_abundance"] >= DEFAULT_MIN_ISOTOPE_ABUNDANCE)
    )

    # Check which isotopes are present in predicted
    if resolution == "HIGH":
        # High resolution: check for exact m/z matches
        # rounding to avoid floating point issues
        present_iso_mask = (
            ion_group_filt["mz"]
            .round(DECIMAL_PLACES)
            .is_in(np.round(masses, DECIMAL_PLACES))
        )
    else:
        # Low resolution: check if the values are present within 1 ppm tolerance
        def is_in_1ppm(value, array):
            return bool(
                np.any(np.abs(array - value) / value * 1e6 <= LOW_PPM_THRESHOLD)
            )

        present_iso_mask = (
            ion_group_filt["mz"]
            .map_elements(lambda x: is_in_1ppm(x, masses), return_dtype=pl.Boolean)
            .to_numpy()
        )

    if present_iso_mask.sum() < len(ion_group_filt["mz"]):
        # Some isotopes are missing, rematch may be needed if there are associated samples
        # Add the rest (with abundance >= DEFAULT_MIN_ISOTOPE_ABUNDANCE) target isotopes
        target_isotopes.extend(
            [
                TargetIsotope(
                    target_ion_id=ion_id,
                    target_isotope_id=gen_id(16),
                    mz=mz,
                    relative_abundance=ra,
                    resolution=resolution,
                    target_isotope_formula=form,
                )
                for mz, ra, form in zip(
                    masses[~abundance_mask],
                    abundances[~abundance_mask],
                    formulas[~abundance_mask],
                )
            ]
        )
        return target_isotopes, ion_id
    else:
        # All isotopes from DB are present in predicted
        # Add them to target isotopes with the same IDs to keep matches
        def formula_lookup(mz_value):
            """Finds the formula for a given m/z value from predicted isotopes."""
            idx = np.argmin(np.abs(masses[~abundance_mask] - mz_value))
            return formulas[~abundance_mask][idx]

        for row in ion_group_filt.iter_rows(named=True):
            target_isotopes.append(
                TargetIsotope(
                    target_ion_id=ion_id,
                    target_isotope_id=row["target_isotope_id"],
                    mz=row["mz"],
                    relative_abundance=row["relative_abundance"],
                    resolution=resolution,
                    target_isotope_formula=formula_lookup(row["mz"]),
                )
            )
        return target_isotopes, None


if __name__ == "__main__":
    asyncio.run(run())
