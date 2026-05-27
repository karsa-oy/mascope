"""
Tests for mascope_file.io module.
"""

import os
import shutil

import numpy as np
import pytest
import xarray as xr
import zarr
from conftest import TEST_FILENAME, TEST_MZ_SIZE, TEST_TIME_SIZE

from mascope_file.io import ensure_sparsity_exists, write_peaks


class TestWritePeaks:
    """Tests for write_peaks function and related helpers."""

    @pytest.mark.asyncio
    async def test_full_overwrite_creates_new_zarr(
        self,
        create_peak_timeseries_dataset,
        peak_timeseries_zarr_path,
    ):
        """Test that write_peaks creates a new zarr file when none exists."""
        # Ensure no existing file
        if os.path.exists(peak_timeseries_zarr_path):
            shutil.rmtree(peak_timeseries_zarr_path)

        # Create dataset
        ds = create_peak_timeseries_dataset(fill_with_nan=True)

        # Write peaks (should trigger full overwrite since file doesn't exist)
        await write_peaks(ds, TEST_FILENAME, overwrite=False)

        # Verify file was created
        assert os.path.exists(peak_timeseries_zarr_path)

        # Verify structure
        z = zarr.open(peak_timeseries_zarr_path, mode="r")
        assert "mz" in z
        assert "time" in z
        assert "peak_areas" in z
        assert "peak_heights" in z
        assert "is_timeseries_computed" in z
        assert "is_satellite" in z
        assert "is_weak" in z
        assert "sum_peak_areas" in z
        assert "sum_peak_heights" in z
        assert "signal_to_noise" in z
        assert "polarity" in z

        # Verify dimensions
        assert z["mz"].shape == (TEST_MZ_SIZE,)
        assert z["time"].shape == (TEST_TIME_SIZE,)
        assert z["peak_areas"].shape == (TEST_MZ_SIZE, TEST_TIME_SIZE)

        # Cleanup
        shutil.rmtree(peak_timeseries_zarr_path)

    @pytest.mark.asyncio
    async def test_full_overwrite_with_flag(
        self,
        create_peak_timeseries_dataset,
        peak_timeseries_zarr_path,
    ):
        """Test that write_peaks overwrites existing file when overwrite=True."""
        # Create initial file with specific values
        initial_ds = create_peak_timeseries_dataset(fill_with_nan=True)
        await write_peaks(initial_ds, TEST_FILENAME, overwrite=True)

        # Verify initial file
        initial_zarr = zarr.open(peak_timeseries_zarr_path, mode="r")
        original_mz = initial_zarr["mz"][:]

        # Create new dataset with different m/z values
        new_mz = np.linspace(200.0, 600.0, TEST_MZ_SIZE)  # Different range
        overwritten_ds = create_peak_timeseries_dataset(
            mz_values=new_mz, fill_with_nan=True
        )

        # Overwrite
        await write_peaks(overwritten_ds, TEST_FILENAME, overwrite=True)

        # Verify file was overwritten
        overwritten_zarr = zarr.open(peak_timeseries_zarr_path, mode="r")
        new_mz_stored = overwritten_zarr["mz"][:]

        assert not np.allclose(original_mz, new_mz_stored)
        np.testing.assert_allclose(new_mz, new_mz_stored)

        # Cleanup
        shutil.rmtree(peak_timeseries_zarr_path)

    @pytest.mark.asyncio
    async def test_partial_update_single_mz(
        self,
        existing_peak_timeseries_zarr,
        create_update_dataset,
    ):
        """Test partial update of a single m/z value."""
        # Load existing data to get coordinates
        existing = xr.open_zarr(existing_peak_timeseries_zarr)
        base_mz = existing["mz"].values
        time_vals = existing["time"].values

        # Verify initial state - all NaN
        assert np.all(np.isnan(existing["peak_areas"].values))
        existing.close()

        # Create update for a single m/z (index 5)
        update_indices = [5]
        update_ds = create_update_dataset(base_mz, time_vals, update_indices)

        # Perform partial update
        await write_peaks(update_ds, TEST_FILENAME, overwrite=False)

        # Verify the update
        updated = xr.open_zarr(existing_peak_timeseries_zarr)

        # Index 5 should have non-NaN values
        assert not np.any(np.isnan(updated["peak_areas"].isel(mz=5).values))
        assert not np.any(np.isnan(updated["peak_heights"].isel(mz=5).values))
        assert updated["is_timeseries_computed"].isel(mz=5).values

        # Other indices should still be NaN
        for idx in [0, 1, 2, 3, 4, 6, 7, 8, 9]:
            assert np.all(np.isnan(updated["peak_areas"].isel(mz=idx).values))

        updated.close()

    @pytest.mark.asyncio
    async def test_partial_update_multiple_mz(
        self,
        existing_peak_timeseries_zarr,
        create_update_dataset,
    ):
        """Test partial update of multiple m/z values."""
        # Load existing data
        existing = xr.open_zarr(existing_peak_timeseries_zarr)
        base_mz = existing["mz"].values
        time_vals = existing["time"].values
        existing.close()

        # Create update for multiple m/z values (scattered across chunks)
        update_indices = [2, 7, 12, 18]
        update_ds = create_update_dataset(base_mz, time_vals, update_indices)

        # Perform partial update
        await write_peaks(update_ds, TEST_FILENAME, overwrite=False)

        # Verify the updates
        updated = xr.open_zarr(existing_peak_timeseries_zarr)

        for idx in update_indices:
            assert not np.any(np.isnan(updated["peak_areas"].isel(mz=idx).values)), (
                f"Index {idx} should have non-NaN values"
            )
            assert updated["is_timeseries_computed"].isel(mz=idx).values

        # Verify non-updated indices remain NaN
        non_updated = [i for i in range(TEST_MZ_SIZE) if i not in update_indices]
        for idx in non_updated[:5]:  # Check first few
            assert np.all(np.isnan(updated["peak_areas"].isel(mz=idx).values)), (
                f"Index {idx} should still be NaN"
            )

        updated.close()

    @pytest.mark.asyncio
    async def test_partial_update_preserves_existing_data(
        self,
        existing_peak_timeseries_zarr,
        create_update_dataset,
    ):
        """Test that partial update preserves previously computed values."""
        # Load existing data
        existing = xr.open_zarr(existing_peak_timeseries_zarr)
        base_mz = existing["mz"].values
        time_vals = existing["time"].values
        existing.close()

        # First update: indices 0-4
        update1_indices = [0, 1, 2, 3, 4]
        update1_ds = create_update_dataset(base_mz, time_vals, update1_indices)
        await write_peaks(update1_ds, TEST_FILENAME, overwrite=False)

        # Read the values we just wrote
        after_first = xr.open_zarr(existing_peak_timeseries_zarr)
        first_update_values = (
            after_first["peak_areas"].isel(mz=slice(0, 5)).values.copy()
        )
        after_first.close()

        # Second update: indices 5-9
        update2_indices = [5, 6, 7, 8, 9]
        update2_ds = create_update_dataset(base_mz, time_vals, update2_indices)
        await write_peaks(update2_ds, TEST_FILENAME, overwrite=False)

        # Verify first update values are preserved
        final = xr.open_zarr(existing_peak_timeseries_zarr)

        np.testing.assert_array_equal(
            first_update_values,
            final["peak_areas"].isel(mz=slice(0, 5)).values,
            err_msg="First update values should be preserved after second update",
        )

        # Verify second update was applied
        for idx in update2_indices:
            assert not np.any(np.isnan(final["peak_areas"].isel(mz=idx).values))

        final.close()

    @pytest.mark.asyncio
    async def test_partial_update_data_integrity(
        self,
        existing_peak_timeseries_zarr,
        create_update_dataset,
    ):
        """Test that partial update writes correct values."""
        # Load existing data
        existing = xr.open_zarr(existing_peak_timeseries_zarr)
        base_mz = existing["mz"].values
        time_vals = existing["time"].values
        existing.close()

        # Create update with known values
        update_indices = [10]
        update_ds = create_update_dataset(base_mz, time_vals, update_indices)

        # Store the values we're about to write
        expected_areas = update_ds["peak_areas"].values.copy()
        expected_heights = update_ds["peak_heights"].values.copy()

        # Perform update
        await write_peaks(update_ds, TEST_FILENAME, overwrite=False)

        # Verify exact values
        updated = xr.open_zarr(existing_peak_timeseries_zarr)

        np.testing.assert_array_almost_equal(
            expected_areas,
            updated["peak_areas"].isel(mz=10).values.reshape(1, -1),
            err_msg="peak_areas values should match exactly",
        )
        np.testing.assert_array_almost_equal(
            expected_heights,
            updated["peak_heights"].isel(mz=10).values.reshape(1, -1),
            err_msg="peak_heights values should match exactly",
        )

        updated.close()


class TestWritePeaksEdgeCases:
    """Edge case tests for write_peaks."""

    @pytest.mark.asyncio
    async def test_update_all_mz_values(
        self,
        existing_peak_timeseries_zarr,
        create_update_dataset,
    ):
        """Test updating all m/z values at once."""
        existing = xr.open_zarr(existing_peak_timeseries_zarr)
        base_mz = existing["mz"].values
        time_vals = existing["time"].values
        existing.close()

        # Update all indices
        update_indices = list(range(TEST_MZ_SIZE))
        update_ds = create_update_dataset(base_mz, time_vals, update_indices)

        await write_peaks(update_ds, TEST_FILENAME, overwrite=False)

        # Verify all values are now non-NaN
        updated = xr.open_zarr(existing_peak_timeseries_zarr)
        assert not np.any(np.isnan(updated["peak_areas"].values))
        assert not np.any(np.isnan(updated["peak_heights"].values))
        assert np.all(updated["is_timeseries_computed"].values)

        updated.close()

    @pytest.mark.asyncio
    async def test_update_first_and_last_mz(
        self,
        existing_peak_timeseries_zarr,
        create_update_dataset,
    ):
        """Test updating boundary m/z values (first and last)."""
        existing = xr.open_zarr(existing_peak_timeseries_zarr)
        base_mz = existing["mz"].values
        time_vals = existing["time"].values
        existing.close()

        # Update first and last indices
        update_indices = [0, TEST_MZ_SIZE - 1]
        update_ds = create_update_dataset(base_mz, time_vals, update_indices)

        await write_peaks(update_ds, TEST_FILENAME, overwrite=False)

        updated = xr.open_zarr(existing_peak_timeseries_zarr)

        # First and last should be updated
        assert not np.any(np.isnan(updated["peak_areas"].isel(mz=0).values))
        assert not np.any(np.isnan(updated["peak_areas"].isel(mz=-1).values))

        # Middle values should still be NaN
        assert np.all(np.isnan(updated["peak_areas"].isel(mz=10).values))

        updated.close()

    @pytest.mark.asyncio
    async def test_repeated_updates_same_mz(
        self,
        existing_peak_timeseries_zarr,
        create_update_dataset,
    ):
        """Test that repeated updates to the same m/z overwrite previous values."""
        existing = xr.open_zarr(existing_peak_timeseries_zarr)
        base_mz = existing["mz"].values
        time_vals = existing["time"].values
        existing.close()

        # First update with seed=42
        update_indices = [5]
        update1_ds = create_update_dataset(base_mz, time_vals, update_indices, seed=42)
        await write_peaks(update1_ds, TEST_FILENAME, overwrite=False)

        # Read first values
        after_first = xr.open_zarr(existing_peak_timeseries_zarr)
        first_values = after_first["peak_areas"].isel(mz=5).values.copy()
        after_first.close()

        # Second update with different seed for different values
        update2_ds = create_update_dataset(base_mz, time_vals, update_indices, seed=99)
        await write_peaks(update2_ds, TEST_FILENAME, overwrite=False)

        # Read second values
        after_second = xr.open_zarr(existing_peak_timeseries_zarr)
        second_values = after_second["peak_areas"].isel(mz=5).values
        after_second.close()

        # Values should have changed
        assert not np.allclose(first_values, second_values)


class TestEnsureSparsityExists:
    """Tests for ensure_sparsity_exists backwards compatibility function."""

    def test_returns_false_when_sparsity_already_present(
        self,
        existing_peak_timeseries_zarr,
    ):
        """Test that no migration occurs if sparsity already exists."""
        # The fixture now includes sparsity, so it should already be present
        result = ensure_sparsity_exists(TEST_FILENAME)
        assert result is False

    def test_creates_sparsity_for_zarr_without_it(
        self,
        peak_timeseries_zarr_path,
        create_peak_timeseries_dataset,
    ):
        """Test that sparsity is created when missing from zarr file."""
        # Create a dataset WITHOUT sparsity to simulate an old zarr
        ds = create_peak_timeseries_dataset(fill_with_nan=True)
        ds = ds.drop_vars("sparsity")
        ds.to_zarr(peak_timeseries_zarr_path, mode="w")

        # Verify sparsity is missing
        z = zarr.open(peak_timeseries_zarr_path, mode="r")
        assert "sparsity" not in z

        # Run migration
        result = ensure_sparsity_exists(TEST_FILENAME)
        assert result is True

        # Verify sparsity was created
        z = zarr.open(peak_timeseries_zarr_path, mode="r")
        assert "sparsity" in z
        assert z["sparsity"].shape == (TEST_MZ_SIZE,)
        assert z["sparsity"].dtype == np.float64

        # All should be 0.0 since no timeseries was computed
        assert np.all(z["sparsity"][:] == 0.0)

        # Verify xarray dimension metadata
        assert z["sparsity"].attrs["_ARRAY_DIMENSIONS"] == ["mz"]

        # Cleanup
        shutil.rmtree(peak_timeseries_zarr_path)

    def test_computes_sparsity_for_computed_peaks_with_gaps(
        self,
        peak_timeseries_zarr_path,
        create_peak_timeseries_dataset,
    ):
        """Test that sparsity=True for computed peaks with heights <= 0."""
        ds = create_peak_timeseries_dataset(fill_with_nan=False)
        ds = ds.drop_vars("sparsity")

        # Mark some peaks as computed
        ds["is_timeseries_computed"].values[0] = True
        ds["is_timeseries_computed"].values[1] = True
        ds["is_timeseries_computed"].values[2] = True

        # Make peak 0 have a zero height (sparse)
        ds["peak_heights"].values[0, 5] = 0.0

        # Make peak 1 have a negative height (sparse)
        ds["peak_heights"].values[1, 3] = -1.0

        # Peak 2 remains all positive (not sparse)
        ds["peak_heights"].values[2, :] = np.abs(ds["peak_heights"].values[2, :]) + 1.0

        # Make peak 0 also have a NaN height (counts as sparse)
        ds["peak_heights"].values[0, 6] = np.nan

        ds.to_zarr(peak_timeseries_zarr_path, mode="w")

        # Run migration
        result = ensure_sparsity_exists(TEST_FILENAME)
        assert result is True

        # Verify results
        z = zarr.open(peak_timeseries_zarr_path, mode="r")
        sparsity = z["sparsity"][:]
        n_time = ds.sizes["time"]

        assert sparsity[0] == pytest.approx(2.0 / n_time)  # 1 zero + 1 NaN height
        assert sparsity[1] == pytest.approx(1.0 / n_time)  # 1 negative height
        assert sparsity[2] == 0.0  # all positive
        # Uncomputed peaks default to 0.0
        assert np.all(sparsity[3:] == 0.0)

        # Cleanup
        shutil.rmtree(peak_timeseries_zarr_path)

    def test_returns_false_when_zarr_does_not_exist(
        self,
        sample_file_path,
        peak_timeseries_zarr_path,
    ):
        """Test that no error is raised when zarr file doesn't exist."""
        # Ensure the zarr file does not exist
        if os.path.exists(peak_timeseries_zarr_path):
            shutil.rmtree(peak_timeseries_zarr_path)
        result = ensure_sparsity_exists(TEST_FILENAME)
        assert result is False

    @pytest.mark.asyncio
    async def test_partial_update_includes_sparsity(
        self,
        existing_peak_timeseries_zarr,
        create_update_dataset,
    ):
        """Test that partial updates correctly write sparsity values."""
        existing = xr.open_zarr(existing_peak_timeseries_zarr)
        base_mz = existing["mz"].values
        time_vals = existing["time"].values
        existing.close()

        # Create update where some peaks are sparse
        update_indices = [3, 7]
        update_ds = create_update_dataset(base_mz, time_vals, update_indices)

        # Make peak at index 0 of the update (mz index 3) sparse
        update_ds["peak_heights"].values[0, 2] = -1.0

        # Add sparsity to the update dataset
        sparsity_vals = (
            np.sum(update_ds["peak_heights"].values <= 0, axis=1)
            / update_ds.sizes["time"]
        )
        update_ds["sparsity"] = (["mz"], sparsity_vals)

        await write_peaks(update_ds, TEST_FILENAME, overwrite=False)

        # Verify
        updated = xr.open_zarr(existing_peak_timeseries_zarr)
        assert updated["sparsity"].isel(mz=3).values > 0.0  # has negative height
        assert updated["sparsity"].isel(mz=7).values == 0.0  # all positive
        updated.close()
