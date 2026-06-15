"""Conftest file for thermo tests. Defines fixtures for test data and common setup."""

from pathlib import Path


_TESTS_DIR = Path(__file__).parent

# Directory of sample .raw files. Only the two small KORBI files are committed;
# tests that need other acquisitions (e.g. an MS² file) discover them at runtime
# and skip when absent, so the suite stays portable.
TEST_FILES_DIR = _TESTS_DIR / "test_files"

POS_ORBI_FILE_PATH = str(TEST_FILES_DIR / "KORBI2_AMB_POS_20260109174345.raw")
NEG_ORBI_FILE_PATH = str(TEST_FILES_DIR / "KORBI2_AMB_NEG_20260108144525.raw")
