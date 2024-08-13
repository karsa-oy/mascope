# TODO general
# - Break down the code into smaller functions to improve readability and maintainability
# - Utilize `pytest` fixtures to handle setup and teardown processes
# - Improve error handling to provide more informative error messages
# - Ensure all tests that can benefit from parameterization
# - Find a more robust mechanism for handling timeouts and retries (tenacity?)

import asyncio
import json
import subprocess
import time
import os
from pathlib import Path
import glob
import shutil
import requests
import pandas as pd
import numpy as np
from mascope_lib.file_func import get_instrument_type
from mascope_lib.peak import detect_peaks
import pytest
from tests.config import *

from mascope_server.api.controllers.match.lib.match_compute import (
    compute_match_isotopes,
)

import mascope_runtime as runtime

logger = runtime.logger.service("backend")

# Load targets
with open(TARGETS_PATH, encoding="utf8") as file:
    target_isotopes = json.load(file)
# Convert target list to DataFrame
target_isotopes_df = pd.DataFrame(target_isotopes["data"])


def get_true_matches(filename):
    """Get precomputed macthes from json file"""
    if ".json" not in filename:
        filename += ".json"
    with open(
        os.path.join(BASE_PATH, "expected_matches", filename), encoding="utf8"
    ) as file:
        return pd.json_normalize(json.load(file))


def get_test_peak_shape(filename):
    """Get precomputed peak shape from json file"""
    if ".json" not in filename:
        filename += ".json"
    with open(
        os.path.join(BASE_PATH, "peak_shapes", filename), encoding="utf8"
    ) as file:
        return json.load(file)


def get_test_resolution_function(filename):
    """Get precomputed resolution function from json file"""
    # Load resolution functions
    with open(RES_FUNCTIONS_PATH, encoding="utf8") as file:
        res_funcs = json.load(file)

    if "tof" in filename.lower():
        R0, mz0, dmz = [res_funcs[filename][i] for i in ["R0", "m0", "dm"]]
        return lambda mz: R0 - R0 / (1 + np.exp((mz - mz0) / dmz))
    if "orbi" in filename.lower():
        R_orb_coef = res_funcs[filename]["a"]
        return lambda mz: R_orb_coef / np.sqrt(mz)
    return None


def clean_folder(folder):
    """Delete all files and folders in the folder"""
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except OSError as e:
            logger.error(f"Failed to delete {file_path}. Reason: {e}")


def run_convertion_server(st: str):
    """Run file convertion server as a separate process"""
    command = f"poetry run file-converter --st {st} --source {WATCH_PATH}"
    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    return process


def check_test_server_running(url):
    response = requests.get(url, timeout=START_TIMEOUT)

    if response.status_code == 200:
        return True
    else:
        raise RuntimeError("Run test Mascope server first")


def test_file_converter():
    """Checks if the file convertion server is alive, performs test file convertion"""
    # Check if the test Mascope server is alive
    check_test_server_running(TEST_SERVER_URL)
    # Clean folder with converted test files
    clean_folder(CONVERTED_FILES_PATH)

    # Check file converters, ext for extension
    for ext in ("Raw", "H5"):
        convertion_process = run_convertion_server(ext)
        # Wait for the server to start
        time.sleep(START_TIMEOUT)
        # Check if the server is running
        assert convertion_process.poll() is None, "Server failed to start"

        if convertion_process.poll() is None:
            # Copy file to the convertion folder
            for file_path in file_dict[ext]:
                shutil.copy2(file_path, WATCH_PATH)

            # Keep checking if convertion is completed
            time_passed = 0
            time_step = 10
            while time_passed < CONVERTION_TIMEOUT:
                # Check if files left in convertion folder
                if not glob.glob(os.path.join(WATCH_PATH, f"*.{ext.lower()}")):
                    break
                time.sleep(time_step)
                time_passed += time_step
            # Check if timeout exceeded
            if time_passed > CONVERTION_TIMEOUT:
                raise TimeoutError("File convertion takes too long")

        # Terminate the server process after testing
        convertion_process.terminate()
        try:
            convertion_process.wait(timeout=START_TIMEOUT)
        except subprocess.TimeoutExpired:
            convertion_process.kill()


def get_filename(filepath):
    """Return proper filename from the"""
    # TODO find better way to handle _- and _+ at the end of filenames
    # Get list of filenames available
    list_of_filenames = os.listdir(os.path.join(BASE_PATH, "peak_shapes"))
    filename = Path(filepath).stem.replace(" ", "_")
    # FInd proper name in list_of_filenames and remove json extension
    filename = [
        fname.replace(".json", "") for fname in list_of_filenames if filename in fname
    ][0]
    return filename


@pytest.mark.parametrize("filepath", file_dict["Raw"] + file_dict["H5"])
def test_detect_peaks(filepath):
    """Test peak detection for a list of files"""
    filename = get_filename(filepath)
    try:
        if "tof" in filepath.lower():
            instrument_type = "tof"
        if "orbi" in filepath.lower():
            instrument_type = "orbi"

        # Get instrument functions
        peakshape = get_test_peak_shape(filename)
        resolution_function = get_test_resolution_function(filename)
        # TODO Get instrument functions from the database
        # peakshape, resolution_function = asyncio.run(
        #     read_instrument_functions(filename=filename)
        # )

        sample_file_data, all_peak_mzs = asyncio.run(
            detect_peaks(
                filename=filename,  # remove extension
                instrument_functions=(peakshape, resolution_function),
                add_peak_threshold=0.9,
                # u_list=np.arange(200, 300, 1),  # for testing
                max_n_peaks=5,
                if_exists="replace",
                dmz=0.5,
                return_peak_mzs=True,
                instrument_type=instrument_type,
            )
        )
        # Check if there are fitted peaks
        assert len(all_peak_mzs) != 0, "No peaks fitted!"
        # TODO
        # QUESTIONS:
        # - maybe it's enouph to just check that fitting happens?
        # OPTIONS for testing
        # - Check if the output has expected type/shape/length
    except Exception:
        pytest.fail(f"Peak detection failed for {filename}")


@pytest.mark.parametrize("filepath", file_dict["Raw"] + file_dict["H5"])
def test_matching(filepath):
    """Test peak matching"""
    filename = get_filename(filepath)
    try:
        # Get precomputed "true" matches
        true_matches = get_true_matches(filename)
        # Get instrument functions
        peakshape = get_test_peak_shape(filename)
        resolution_function = get_test_resolution_function(filename)
        # TODO Get instrument functions from the database
        # peakshape, resolution_function = asyncio.run(
        #     read_instrument_functions(filename=filename)
        # )

        match_isotope_df = asyncio.run(
            compute_match_isotopes(
                filename,
                target_isotopes_df,
                instrument_functions=(peakshape, resolution_function),
                min_isotope_abundance=0.2,
            )
        )
        # Filter dataframes
        df_query = "match_isotope_correlation > 0.9"
        true_matches = true_matches.query(df_query)
        match_isotope_df = match_isotope_df.query(df_query)
        # Check if same matches found as in True matches
        assert set(match_isotope_df["target_ion_id"]) == set(
            true_matches["target_ion_id"]
        ), "Matches do not match!"
    except Exception:
        pytest.fail(f"Matching failed for {filename}")
