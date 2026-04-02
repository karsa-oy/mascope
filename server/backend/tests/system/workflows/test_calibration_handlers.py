import os
import warnings

import pytest
from utils import FakeNotification, collect_samples, get_orbi_raw_files_collection

from mascope_backend.api.controllers.calibration.lib.calibration_mz_fit import (
    get_calibration_handler,
)
from mascope_backend.api.models.calibration.calibration_pydantic_model import (
    CalibrationFitParams,
    OrbiCalibrationParams,
)
from mascope_backend.api.new.ionization.modes.service import get_ionization_mode
from mascope_backend.api.new.ionization.modes.util import (
    fetch_sample_ionization_mechanism_ids,
)
from mascope_backend.db import init_db


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
        mechanisms = await fetch_sample_ionization_mechanism_ids(sample.sample_item_id)
        ionization_mode_response = await get_ionization_mode(sample.ionization_mode_id)
        ionization_mode = ionization_mode_response["data"]
        calibration_collection_id = ionization_mode["calibration_collection_id"]
        orbi_calibration_params = OrbiCalibrationParams()
        polarity = ionization_mode.get("ionization_mode_polarity")
        calibration_fit_parameters = CalibrationFitParams(
            filename=sample.filename,
            calibration_collection_id=calibration_collection_id,
            ionization_mechanism_ids=mechanisms,
            polarity=polarity,
            **orbi_calibration_params.model_dump(),
        )
        calibration_handler = get_calibration_handler(
            sample.filename, calibration_fit_parameters, fake_notification
        )
        await calibration_handler.fit()
        if calibration_handler.warning:
            warnings.warn(f"{sample.filename}: {calibration_handler.warning}")
        if calibration_handler.warning != "No calibration peaks found":
            assert calibration_handler.fit_result is not None, (
                f"Failed to fit calibration for {filetype} ({sample.filename})"
            )
