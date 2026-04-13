import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import xarray as xr


SIGNAL_TEST_FILENAME = "OrbiTest_1001.01.01_12h00m00s_TestFile"


@pytest.fixture(scope="session")
def temp_filestore():
    temp_dir = tempfile.mkdtemp(prefix="mascope_signal_test_filestore_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(autouse=True)
def mock_runtime(temp_filestore):
    def mock_filestore(*args):
        return os.path.join(temp_filestore, *args)

    mock_logger = MagicMock()

    with (
        patch("mascope_file.name.runtime") as mock_name_runtime,
        patch("mascope_file.io.runtime") as mock_io_runtime,
        patch("mascope_signal.compute.runtime") as mock_compute_runtime,
    ):
        mock_name_runtime.filestore = mock_filestore
        mock_io_runtime.filestore = mock_filestore
        mock_io_runtime.logger = mock_logger
        mock_compute_runtime.logger = mock_logger

        yield mock_name_runtime


@pytest.fixture
def sample_file_path(temp_filestore):
    sample_path = os.path.join(
        temp_filestore,
        "OrbiTest",
        "1001.01.01",
        SIGNAL_TEST_FILENAME,
    )
    if os.path.exists(sample_path):
        shutil.rmtree(sample_path, ignore_errors=True)
    os.makedirs(sample_path, exist_ok=True)

    props_path = os.path.join(sample_path, ".props")
    with open(props_path, "w") as f:
        f.write('{"mz_calibration": null}')

    yield sample_path

    shutil.rmtree(sample_path, ignore_errors=True)


@pytest.fixture
def signal_dataset():
    time_values = np.array([0.0, 1.0, 2.0], dtype=np.float64)
    mz_values = np.array([100.0, 101.0, 102.0], dtype=np.float64)
    signal_values = np.array(
        [
            [1.0, 2.0, 3.0],
            [4.0, 5.0, 6.0],
            [7.0, 8.0, 9.0],
        ],
        dtype=np.float64,
    )
    return xr.Dataset(
        {"signal": (("time", "mz"), signal_values)},
        coords={"time": time_values, "mz": mz_values},
    )
