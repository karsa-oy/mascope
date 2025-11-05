"""
Migration script for v38: Merge peak_areas and peak_heights into peak_timeseries,
and add new variables
"""

import asyncio
import os
import shutil
import pandas as pd
import numpy as np
from tqdm import tqdm
import contextlib

from sqlalchemy import select

from mascope_backend.db import async_session, configure_database_engine
from mascope_backend.db.ops.backup import create_db_backup
from mascope_backend.db.models import SampleFile
from mascope_backend.api.new.instrument_configs.lib import read_instrument_functions

import mascope_file.name as m_name
import mascope_file.io as m_io
import mascope_signal.compute as m_compute
from mascope_signal.peak import get_peak_detector

from mascope_tools.alignment.utils import flag_satellite_peaks

from mascope_backend.runtime import runtime


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
    # Create backup before migration
    await create_db_backup()

    # Setup new database version
    old_version = 37
    new_version = 38
    old_db_path = os.path.join(runtime.config.database, f"mascope.v{old_version}.db")
    new_db_path = os.path.join(runtime.config.database, f"mascope.v{new_version}.db")

    # Copy database file to new version
    shutil.copyfile(old_db_path, new_db_path)

    await configure_database_engine(new_version)
    runtime.logger.info(
        f"Starting v{new_version} migration: merging peak_areas and peak_heights."
    )

    async with async_session() as session:
        stmt = select(SampleFile)
        result = await session.execute(stmt)
        sample_files = result.scalars().all()

    sample_to_recompute = []

    # --- First pass: try migrating each sample file ---
    with suppress_logger(runtime.logger):
        for sample_file in tqdm(sample_files):
            try:
                migration_helper = migration_helper_factory(sample_file)
                await migration_helper.migrate()
            except PolarityException as pe:
                tqdm.write(f"WARNING: {pe}")
                sample_to_recompute.append(sample_file)
            except Exception as e:
                tqdm.write(f"Error processing sample file {sample_file.filename}: {e}")
                sample_to_recompute.append(sample_file)

    # --- Second pass: recompute peaks for samples that failed first pass ---
    with suppress_logger(runtime.logger):
        for sample_file in tqdm(sample_to_recompute):
            try:
                instrument_functions = await read_instrument_functions(
                    filename=sample_file.filename
                )
                peak_detector = get_peak_detector(
                    sample_file.filename, instrument_functions
                )
                await peak_detector.detect_peaks()
                peak_detector.write_peaks_to_zarr()
                BaseMigrationHelper.delete_old_zarr_files(sample_file.filename)
            except Exception as e:
                tqdm.write(
                    f"Error recomputing peaks for sample file {sample_file.filename}: {e}"
                )


class BaseMigrationHelper:
    def __init__(self, sample_file: SampleFile):
        self.sample_file = sample_file
        self.peak_timeseries = m_io.load_file(
            sample_file.filename, vars=["peak_areas", "peak_heights"]
        )

    def assign_peak_sums(self):
        """Computes sums for areas and heights and assigns to peak_timeseries"""
        peak_areas_sum = self.peak_timeseries["peak_areas"].sum(dim="time")
        peak_heights_sum = self.peak_timeseries["peak_heights"].sum(dim="time")
        self.peak_timeseries = self.peak_timeseries.assign(
            {
                "sum_peak_areas": peak_areas_sum,
                "sum_peak_heights": peak_heights_sum,
            }
        )

    def flag_satellites(self):
        """Default implementation: no satellite flagging."""
        is_satellite = np.full(self.peak_timeseries.mz.shape, False, dtype=bool)
        self.peak_timeseries = self.peak_timeseries.assign(
            {"is_satellite": (("mz"), is_satellite)}
        )

    def flag_weak_peaks(self):
        """Flag all peaks as non-weak.

        For TOF data, weak peak detection is not performed.
        For Orbitrap data, we filtered out peaks below S/N threshold during detection,
        so all remaining peaks are considered strong.
        """
        is_weak = np.full(self.peak_timeseries.mz.shape, False, dtype=bool)
        self.peak_timeseries = self.peak_timeseries.assign(
            {"is_weak": (("mz"), is_weak)}
        )

    def flag_computed_timeseries(self):
        """Flag all peaks as having computed timeseries.

        For both TOF and Orbitrap data, we used to compute timeseries for all detected peaks.
        """
        is_timeseries_computed = np.full(
            self.peak_timeseries.mz.shape, True, dtype=bool
        )
        self.peak_timeseries = self.peak_timeseries.assign(
            {"is_timeseries_computed": (("mz"), is_timeseries_computed)}
        )

    def add_polarity(self):
        polarity = m_compute.get_polarity_options(self.sample_file.filename)
        if polarity == "+-":
            raise PolarityException(
                f"Sample file {self.sample_file.filename} has mixed polarity, cannot assign single polarity."
            )
        polarity_arr = np.full(self.peak_timeseries.mz.shape, polarity, dtype="U1")
        self.peak_timeseries = self.peak_timeseries.assign(
            {"polarity": (("mz"), polarity_arr)}
        )

    async def add_signal_to_noise(self):
        raise NotImplementedError(
            "add_signal_to_noise must be implemented in subclasses."
        )

    def write_peak_timeseries(self):
        m_io.write_peaks(
            self.peak_timeseries, self.sample_file.filename, overwrite=True
        )

    @staticmethod
    def delete_old_zarr_files(filename):
        """Delete old peak_areas and peak_heights zarr files."""
        peak_areas_path = m_name.filename_to_zarr_path(filename, "peak_areas")
        peak_heights_path = m_name.filename_to_zarr_path(filename, "peak_heights")
        if os.path.exists(peak_areas_path):
            shutil.rmtree(peak_areas_path)
        if os.path.exists(peak_heights_path):
            shutil.rmtree(peak_heights_path)

    async def migrate(self):
        self.assign_peak_sums()
        self.flag_satellites()
        self.flag_weak_peaks()
        self.flag_computed_timeseries()
        self.add_polarity()
        await self.add_signal_to_noise()
        self.write_peak_timeseries()
        self.delete_old_zarr_files(self.sample_file.filename)


class OrbiRawMigrationHelper(BaseMigrationHelper):
    def flag_satellites(self):
        peaks_df = pd.DataFrame(
            {
                "mz": self.peak_timeseries.mz.values,
                "intensity": self.peak_timeseries.sum_peak_heights.values,
            }
        )
        peaks_df = flag_satellite_peaks(peaks_df)
        self.peak_timeseries = self.peak_timeseries.assign(
            {"is_satellite": (("mz"), peaks_df["is_satellite_peak"].values)}
        )

    async def add_signal_to_noise(
        self,
    ) -> np.ndarray:
        """Extract pre-computed signal-to-noise ratio from raw Orbitrap data.
        interpolated onto peak m/z values.

        Polarity is ignored since mixed polarity files would have raised an exception earlier
        and will be recomputed separately.
        """
        peak_mzs, _, _, signal_to_noise = m_compute.get_orbi_centroids(
            self.sample_file.filename,
        )
        snr_interpolated = np.interp(
            self.peak_timeseries.mz.values,
            peak_mzs,
            signal_to_noise,
            left=np.nan,
            right=np.nan,
        )
        self.peak_timeseries = self.peak_timeseries.assign(
            {"signal_to_noise": (("mz"), snr_interpolated)}
        )


class TofH5MigrationHelper(BaseMigrationHelper):
    async def add_signal_to_noise(
        self,
    ) -> np.ndarray:
        """Compute signal-to-noise ratio for each peak based on baseline noise."""
        sum_signal = m_compute.get_sum_signal(self.sample_file.filename)
        mz_axis = sum_signal.mz.values
        signal = sum_signal.values
        peak_mzs = self.peak_timeseries.mz.values
        peak_heights = self.peak_timeseries.sum_peak_heights.values
        snr = np.empty(len(peak_mzs), dtype=np.float64)

        # Compute exclusion zone from the resolution function
        _, resolution_function = await read_instrument_functions(
            self.sample_file.filename
        )
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

        self.peak_timeseries = self.peak_timeseries.assign(
            {"signal_to_noise": (("mz"), snr)}
        )


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


def migration_helper_factory(sample_file: SampleFile) -> BaseMigrationHelper:
    sample_file_type = m_name.get_sample_file_type(sample_file.filename)
    try:
        return MIGRATION_HELPER_MAP[sample_file_type](sample_file)
    except KeyError:
        raise ValueError(f"Unsupported sample file type: {sample_file_type}")


if __name__ == "__main__":
    asyncio.run(run())
