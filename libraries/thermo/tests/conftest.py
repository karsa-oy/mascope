"""Conftest file for thermo tests. Defines fixtures for test data and common setup."""

import os
from pathlib import Path

import pytest

from mascope_thermo.lib import thermo_available


_TESTS_DIR = Path(__file__).parent

# Directory of sample .raw files. Only the two small committed sample files
# ship; tests that need other acquisitions (e.g. an MS2 file) discover them at
# runtime and skip when absent, so the suite stays portable. Override with
# MASCOPE_THERMO_TEST_FILES_DIR to run the file-agnostic parity suite against a
# broader local corpus (e.g. a stratified sample of the filestore).
TEST_FILES_DIR = Path(
    os.environ.get("MASCOPE_THERMO_TEST_FILES_DIR", _TESTS_DIR / "test_files")
)

POS_ORBI_FILE_PATH = str(TEST_FILES_DIR / "KORBI2_AMB_POS_20260109174345.raw")
NEG_ORBI_FILE_PATH = str(TEST_FILES_DIR / "KORBI2_AMB_NEG_20260108144525.raw")


@pytest.fixture(params=["thermo", "opentfraw"])
def backend(request, monkeypatch):
    """Run a contract test once per reader backend.

    Sets ``MASCOPE_THERMO_BACKEND`` for the test. The OpenTFRaw backend (the
    default, via the pinned ``mascope-opentfraw`` fork) is always available and
    expected to pass. The Thermo backend needs the proprietary RawFileReader
    DLLs, which Mascope does not ship, so its runs are skipped unless
    ``MASCOPE_THERMO_DLL_DIR`` points at them.

    Tests/fixtures that build per-test state by *calling* a backend function must
    depend on this fixture (directly or via an autouse setup fixture) so the env
    var is set before the call -- a plain ``setup_method`` runs too early.
    """
    if request.param == "thermo" and not thermo_available():
        pytest.skip(
            "Thermo backend unavailable; set MASCOPE_THERMO_DLL_DIR to the "
            "RawFileReader DLLs to run it."
        )
    monkeypatch.setenv("MASCOPE_THERMO_BACKEND", request.param)
    return request.param


def read_or_xfail(fn, *args, **kwargs):
    """Call a backend read inside *fixture setup*, turning a not-yet-implemented
    backend into an xfail.

    The ``backend`` fixture's ``xfail(raises=NotImplementedError)`` only covers a
    test's *call* phase; an exception during fixture setup is otherwise reported
    as an error. An imperative ``pytest.xfail()`` works in setup, and -- since it
    only fires when the call actually raises -- the test still runs (and XPASSes)
    once the backend is implemented.
    """
    try:
        return fn(*args, **kwargs)
    except NotImplementedError as exc:
        pytest.xfail(str(exc))
