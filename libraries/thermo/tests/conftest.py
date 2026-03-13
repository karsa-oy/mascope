"""Conftest file for thermo tests. Defines fixtures for test data and common setup."""

from pathlib import Path

_TESTS_DIR = Path(__file__).parent

POS_ORBI_FILE_PATH = str(
    _TESTS_DIR / "test_files" / "KORBI2_AMB_POS_20260109174345.raw"
)
NEG_ORBI_FILE_PATH = str(
    _TESTS_DIR / "test_files" / "KORBI2_AMB_NEG_20260108144525.raw"
)
