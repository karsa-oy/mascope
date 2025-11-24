"""
Migration script for v38: Merge peak_areas and peak_heights into peak_timeseries,
and add new variables
"""

import asyncio
import os
import shutil
import numpy as np
from tqdm import tqdm
import contextlib
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

from sqlalchemy import select

from mascope_backend.db import async_session, configure_database_engine
from mascope_backend.db.ops.backup import create_db_backup
from mascope_backend.db.models import SampleFile
from mascope_backend.db.id import gen_id
from mascope_backend.api.new.instrument_configs.lib import read_instrument_functions

import mascope_file.name as m_name
import mascope_file.io as m_io
import mascope_signal.compute as m_compute
from mascope_signal.peak import get_peak_detector, PEAK_ID_LENGTH

from mascope_tools.alignment.utils import DEFAULT_TIGHT_WINDOW_PPM, NEUTRON_MASS

from mascope_backend.runtime import runtime


cpu_cores = os.cpu_count()
# thread pool for I/O-bound and mixed tasks, reserve 2 cores for system responsiveness
thread_pool = ThreadPoolExecutor(max_workers=max(1, cpu_cores - 2))
# process pool for CPU-bound tasks with heavy disk I/O, serialization, etc.
# Limit process pool to avoid disk saturation. Empirically: number of physical cores / 2.
process_pool = ProcessPoolExecutor(max_workers=max(1, cpu_cores // 2))
# Semaphore to limit concurrent migrations globally.
semaphore = asyncio.Semaphore(max(1, cpu_cores - 2))


class PolarityException(Exception):
    pass


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
    # Create backup and configure database engine
    await create_db_backup()

    # Setup new database version
    old_version = 37
    new_version = 38
    old_db_path = os.path.join(runtime.config.database, f"mascope.v{old_version}.db")
    new_db_path = os.path.join(runtime.config.database, f"mascope.v{new_version}.db")

    shutil.copyfile(old_db_path, new_db_path)

    await configure_database_engine(new_version)
    runtime.logger.info(
        f"Starting v{new_version} migration: merging peak_areas and peak_heights."
    )

    # Fetch all sample filenames
    async with async_session() as session:
        stmt = select(SampleFile.filename)
        result = await session.execute(stmt)
        filenames = result.scalars().all()

    # --- First pass: concurrent migration of sample files ---
    async def bounded_migrate(filename):
        async with semaphore:
            return await migrate_sample_file(filename, thread_pool, process_pool)

    sample_to_recompute = []
    with suppress_logger(runtime.logger):
        tasks = [bounded_migrate(sf) for sf in filenames]
        for migration_task_future in tqdm(
            asyncio.as_completed(tasks), total=len(tasks)
        ):
            filename, exception = await migration_task_future
            if exception is not None:
                tqdm.write(
                    f"WARNING: {exception}"
                    if isinstance(exception, PolarityException)
                    else f"Error processing sample file {filename}: {exception}"
                )
                sample_to_recompute.append(filename)

    # --- Second pass: recompute peaks for samples that failed first pass ---
    # Not so many expected, so do sequentially to avoid overwhelming system.
    with suppress_logger(runtime.logger):
        for filename in tqdm(sample_to_recompute):
            try:
                instrument_functions = await read_instrument_functions(
                    filename=filename
                )
                peak_detector = get_peak_detector(filename, instrument_functions)
                await peak_detector.detect_peaks()
                await peak_detector.write_peaks_to_zarr()
                BaseMigrationHelper.delete_old_zarr_files(filename)
            except Exception as e:
                tqdm.write(f"Error recomputing peaks for sample file {filename}: {e}")


async def migrate_sample_file(
    filename: str,
    thread_pool: ThreadPoolExecutor,
    process_pool: ProcessPoolExecutor,
) -> tuple[str, Exception | None]:
    """Migrate a single sample file. Returns (filename, exception) tuple."""
    try:
        loop = asyncio.get_running_loop()
        migration_helper = await loop.run_in_executor(
            thread_pool, migration_helper_factory, filename
        )
        await migration_helper.migrate(thread_pool, process_pool)
        return filename, None
    except PolarityException as pe:
        return filename, pe
    except Exception as e:
        return filename, e


class BaseMigrationHelper:
    def __init__(self, filename: str):
        self.filename = filename
        peak_areas = m_io.load_array(filename, var="peak_areas")
        peak_heights = m_io.load_array(filename, var="peak_heights")
        self.peak_timeseries = peak_areas.assign(
            {"peak_heights": peak_heights.peak_heights}
        )
        self.n_peaks = self.peak_timeseries.mz.shape[0]

    @property
    def sum_peak_areas(self):
        return self.peak_timeseries["peak_areas"].sum(dim="time").values

    @property
    def sum_peak_heights(self):
        return self.peak_timeseries["peak_heights"].sum(dim="time").values

    @property
    def is_satellite(self):
        """Default implementation: no satellite flagging."""
        is_satellite = np.full(self.n_peaks, False, dtype=bool)
        return is_satellite

    @property
    def polarity(self):
        polarity = m_compute.get_polarity_options(self.filename)
        if polarity == "+-":
            raise PolarityException(
                f"Sample file {self.filename} has mixed polarity, cannot assign single polarity."
            )
        return np.full(self.n_peaks, polarity, dtype="U1")

    @property
    def peak_ids(self):
        return [gen_id(PEAK_ID_LENGTH) for _ in range(self.n_peaks)]

    async def signal_to_noise(self):
        raise NotImplementedError("signal_to_noise must be implemented in subclasses.")

    async def write_peak_timeseries(self, process_pool: ProcessPoolExecutor):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            process_pool,
            write_peaks,
            self.peak_timeseries,
            self.filename,
        )

    @staticmethod
    def delete_old_zarr_files(filename):
        """Delete old peak_areas and peak_heights zarr files."""
        peak_areas_path = m_name.filename_to_zarr_path(filename, "peak_areas")
        peak_heights_path = m_name.filename_to_zarr_path(filename, "peak_heights")
        peak_area_sync_path = peak_areas_path.replace(".zarr", ".sync")
        peak_height_sync_path = peak_heights_path.replace(".zarr", ".sync")
        for path in [
            peak_areas_path,
            peak_heights_path,
            peak_area_sync_path,
            peak_height_sync_path,
        ]:
            if os.path.exists(path):
                shutil.rmtree(path)

    async def migrate(
        self,
        thread_pool: ThreadPoolExecutor,
        process_pool: ProcessPoolExecutor,
    ) -> None:
        loop = asyncio.get_running_loop()

        def _sync_stage() -> dict:
            vars_to_add = {
                "sum_peak_areas": (("mz"), self.sum_peak_areas),
                "sum_peak_heights": (("mz"), self.sum_peak_heights),
                "polarity": (("mz"), self.polarity),
                "peak_id": (("mz"), self.peak_ids),
                "is_satellite": (("mz"), self.is_satellite),
                "is_timeseries_computed": (("mz"), np.ones(self.n_peaks, dtype=bool)),
                "is_weak": (("mz"), np.zeros(self.n_peaks, dtype=bool)),
            }
            return vars_to_add

        # Compute and assign all non-async variables in thread pool.
        vars_to_add = await loop.run_in_executor(thread_pool, _sync_stage)
        # Compute and assign async variables.
        vars_to_add["signal_to_noise"] = (("mz"), await self.signal_to_noise())
        # Bulk assign to avoid multiple copies.
        self.peak_timeseries = self.peak_timeseries.assign(vars_to_add)
        # Write out merged peak_timeseries using process pool.
        await self.write_peak_timeseries(process_pool)
        # Cleanup old separate arrays (thread pool is fine).
        await loop.run_in_executor(
            thread_pool, self.delete_old_zarr_files, self.filename
        )


class OrbiRawMigrationHelper(BaseMigrationHelper):
    @property
    def is_satellite(self):
        return flag_satellite_peaks(
            self.peak_timeseries.mz.values, self.sum_peak_heights
        )

    async def signal_to_noise(
        self,
    ) -> np.ndarray:
        """Extract pre-computed signal-to-noise ratio from raw Orbitrap data.
        interpolated onto peak m/z values.

        Polarity is ignored since mixed polarity files would have raised an exception earlier
        and will be recomputed separately.
        """
        peak_mzs, _, _, signal_to_noise = await m_compute.get_orbi_centroids(
            self.filename,
        )
        snr_interpolated = np.interp(
            self.peak_timeseries.mz.values,
            peak_mzs,
            signal_to_noise,
            left=np.nan,
            right=np.nan,
        )
        return snr_interpolated


class TofH5MigrationHelper(BaseMigrationHelper):
    async def signal_to_noise(
        self,
    ) -> np.ndarray:
        """Compute signal-to-noise ratio for each peak based on baseline noise."""
        sum_signal = m_compute.get_sum_signal(self.filename)
        mz_axis = sum_signal.mz.values
        signal = sum_signal.values
        peak_mzs = self.peak_timeseries.mz.values
        peak_heights = self.peak_timeseries.sum_peak_heights.values
        snr = np.empty(len(peak_mzs), dtype=np.float64)

        # Compute exclusion zone from the resolution function
        _, resolution_function = await read_instrument_functions(self.filename)
        resolutions = resolution_function(peak_mzs)
        exclusion = peak_mzs / resolutions

        # Compute baseline window as 10 times the exclusion zone
        window = 10 * exclusion

        # Vectorized baseline window calculation
        left_min = peak_mzs - window
        left_max = peak_mzs - exclusion
        right_min = peak_mzs + exclusion
        right_max = peak_mzs + window

        # For each peak, select baseline regions and compute noise std
        for i in range(len(peak_mzs)):
            left_mask = (mz_axis >= left_min[i]) & (mz_axis <= left_max[i])
            right_mask = (mz_axis >= right_min[i]) & (mz_axis <= right_max[i])
            baseline = signal[left_mask | right_mask]
            # Use robust estimator if baseline is non-Gaussian
            noise_std = np.std(baseline) if baseline.size > 0 else np.nan
            snr[i] = peak_heights[i] / noise_std if noise_std > 0 else np.nan

        return snr


class TofZarrMigrationHelper(TofH5MigrationHelper):
    pass


class OrbiZarrMigrationHelper(TofH5MigrationHelper):
    pass


MIGRATION_HELPER_MAP = {
    "orbi_raw": OrbiRawMigrationHelper,
    "tof_h5": TofH5MigrationHelper,
    "tof_zarr": TofZarrMigrationHelper,
    "orbi_zarr": OrbiZarrMigrationHelper,
}


def migration_helper_factory(filename: str) -> BaseMigrationHelper:
    sample_file_type = m_name.get_sample_file_type(filename)
    try:
        return MIGRATION_HELPER_MAP[sample_file_type](filename)
    except KeyError:
        raise ValueError(f"Unsupported sample file type: {filename}")


def write_peaks(peak_timeseries, filename: str) -> None:
    """Simplified synchronous m_io.write_peaks to zarr function."""
    peak_timeseries_path = m_name.filename_to_zarr_path(filename, "peak_timeseries")
    synchronizer = m_io.get_zarr_synchronizer(peak_timeseries_path)
    peak_timeseries.to_zarr(peak_timeseries_path, mode="w", synchronizer=synchronizer)


def flag_satellite_peaks(
    mz: np.ndarray,
    intensity: np.ndarray,
    base_peak_percentile: float = 99.9,
    top_n_bases: int | None = 5,
    window_ppm: float = 350.0,
    ratio_max: float = 0.04,
    ratio_min: float = 1e-6,
    symmetry_tolerance_ppm: float = 1.5,
    isotope_tolerance_ppm: float = 2.0,
    charge_range: tuple[int, int] = (1, 2),
) -> np.ndarray:
    """flag_satellite_peaks from mascope_tools but without pandas dependency."""

    # Remove non-positive intensities early (cannot be parents nor satellites).
    valid_mask = intensity > 0
    mz = mz[valid_mask]
    intensity = intensity[valid_mask]

    n_peaks = mz.size

    # Select base peaks (intensity-based).
    base_thr = np.quantile(intensity, base_peak_percentile / 100.0)
    base_candidates = np.flatnonzero(intensity >= base_thr)
    if top_n_bases is not None and base_candidates.size > top_n_bases:
        # Keep top_n_bases highest-intensity indices.
        strongest_local = np.argsort(intensity[base_candidates])[::-1][:top_n_bases]
        base_indices = np.sort(base_candidates[strongest_local])
    else:
        base_indices = base_candidates

    # Precompute charges and isotope delta masses.
    charges = np.arange(charge_range[0], charge_range[1] + 1, dtype=int)
    isotope_deltas = NEUTRON_MASS / charges  # Da

    is_satellite = np.zeros(n_peaks, dtype=bool)

    # Precompute ppm to Da helper inline (avoid extra function call in tight loop).
    def ppm_to_da_local(mass: float, ppm: float) -> float:
        return mass * ppm * 1e-6

    symmetry_ppm = symmetry_tolerance_ppm
    isotope_ppm = isotope_tolerance_ppm
    win_ppm = window_ppm
    ratio_lo = ratio_min
    ratio_hi = ratio_max

    for base_idx in base_indices:
        parent_mz = mz[base_idx]
        parent_intensity = intensity[base_idx]
        if parent_intensity <= 0:
            continue

        win_da = ppm_to_da_local(parent_mz, win_ppm)
        left = np.searchsorted(mz, parent_mz - win_da, side="left")
        right = np.searchsorted(mz, parent_mz + win_da, side="right")

        if right - left <= 1:
            continue

        cand_idx = np.arange(left, right)
        cand_idx = cand_idx[cand_idx != base_idx]
        if cand_idx.size == 0:
            continue

        rel_ratio = intensity[cand_idx] / parent_intensity
        ratio_mask = (rel_ratio >= ratio_lo) & (rel_ratio <= ratio_hi)
        cand_idx = cand_idx[ratio_mask]
        if cand_idx.size == 0:
            continue

        cand_mz = mz[cand_idx]
        dmz = cand_mz - parent_mz

        # Exclude +1 isotopes (only dmz > 0).
        pos_mask = dmz > 0
        if np.any(pos_mask):
            dmz_pos = dmz[pos_mask]
            cand_idx_pos = cand_idx[pos_mask]
            exclude_iso = np.zeros(dmz_pos.size, dtype=bool)
            # Vectorized isotope exclusion.
            for iso_da in isotope_deltas:
                tolerance_da = ppm_to_da_local(parent_mz + iso_da, isotope_ppm)
                exclude_iso |= np.abs(dmz_pos - iso_da) <= tolerance_da
            keep_pos = ~exclude_iso
            # Recombine positive + negative side indices.
            cand_idx = np.concatenate([cand_idx[~pos_mask], cand_idx_pos[keep_pos]])
            dmz = mz[cand_idx] - parent_mz

        if cand_idx.size == 0:
            continue

        # Symmetry detection: match |dmz_left| ≈ dmz_right within tolerance.
        left_mask = dmz < 0
        right_mask = dmz > 0
        left_dmz = -dmz[left_mask]
        right_dmz = dmz[right_mask]
        left_idx = cand_idx[left_mask]
        right_idx = cand_idx[right_mask]

        # Tolerance (Da) computed at parent m/z.
        sym_tol_da = ppm_to_da_local(parent_mz, symmetry_ppm)

        # Use sorted arrays for matching.
        if left_dmz.size and right_dmz.size:
            # For each right offset, search approximate left match.
            # Sort left_dmz for binary search.
            left_order = np.argsort(left_dmz)
            left_dmz_sorted = left_dmz[left_order]
            left_idx_sorted = left_idx[left_order]

            for r_off, r_i in zip(right_dmz, right_idx):
                lo = np.searchsorted(left_dmz_sorted, r_off - sym_tol_da, side="left")
                hi = np.searchsorted(left_dmz_sorted, r_off + sym_tol_da, side="right")
                if hi <= lo:
                    continue
                # Choose closest left offset.
                segment = left_dmz_sorted[lo:hi]
                closest_rel = np.argmin(np.abs(segment - r_off))
                l_i = left_idx_sorted[lo + closest_rel]

                # Compare intensity ratios for similarity.
                r_ratio = intensity[r_i] / parent_intensity
                l_ratio = intensity[l_i] / parent_intensity
                ratio_similarity = min(r_ratio, l_ratio) / max(r_ratio, l_ratio)
                if ratio_similarity >= 0.5:
                    is_satellite[r_i] = True
                    is_satellite[l_i] = True

        # Single-sided satellites (weak, very near parent).
        # Restrict to those still unflagged.
        unresolved = cand_idx[~is_satellite[cand_idx]]
        if unresolved.size:
            tight_window_da = ppm_to_da_local(
                parent_mz, min(win_ppm * 0.5, DEFAULT_TIGHT_WINDOW_PPM)
            )
            near_mask = np.abs(mz[unresolved] - parent_mz) <= tight_window_da
            weak_mask = (intensity[unresolved] / parent_intensity) <= ratio_hi
            final_mask = near_mask & weak_mask
            is_satellite[unresolved[final_mask]] = True
    return is_satellite


if __name__ == "__main__":
    asyncio.run(run())
