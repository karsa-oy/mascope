import os
import pytest
import warnings
from mascope_backend.db import init_db, async_session
from mascope_backend.api.controllers.calibration.lib.calibration_mz_fit import (
    get_calibration_handler,
)
from mascope_backend.api.models.calibration.calibration_pydantic_model import (
    CalibrationFitParams,
)
from mascope_backend.db.models import SampleBatch
from utils import get_orbi_raw_files_collection, collect_samples, FakeNotification


@pytest.mark.asyncio
async def test_calibration_fitting():
    """Currently, this test only checks if the calibration fitting process runs without errors
    for various Orbitrap samples.
    """
    if os.getenv("SKIP_CALIBRATION_FITTING_TEST") == "1":
        pytest.skip("Skipping calibration fitting test while CI/CD is being set up")
    await init_db()
    fake_notification = FakeNotification()
    samples = await collect_samples()

    # Orbi raw tests
    orbi_sample_files = await get_orbi_raw_files_collection(samples)
    for filetype, sample in orbi_sample_files.items():
        async with async_session() as session:
            sample_batch = await session.get(SampleBatch, sample.sample_batch_id)

        build_params = sample_batch.build_params
        calibration_mechs = build_params["calibration_ion_mechanisms"]
        matching_mechs = build_params["ion_mechanisms"]
        mechanisms = calibration_mechs if calibration_mechs else matching_mechs

        calibration_parameters = CalibrationFitParams(
            calibration_collection_id=build_params["calibration_collection"],
            ionization_mechanism_ids=mechanisms,
        )
        calibration_handler = get_calibration_handler(
            sample.filename, calibration_parameters, fake_notification
        )
        await calibration_handler.fit()
        if calibration_handler.warning:
            warnings.warn(f"{sample.filename}: {calibration_handler.warning}")
        if calibration_handler.warning != "No calibration peaks found":
            assert (
                calibration_handler.fit_result is not None
            ), f"Failed to fit calibration for {filetype} ({sample.filename})"
