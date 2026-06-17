"""Conftest file for thermo tests. Defines fixtures for test data and common setup."""

import os
from pathlib import Path

import pytest


_TESTS_DIR = Path(__file__).parent

# Directory of sample .raw files. Only the two small committed sample files
# ship; tests that need other acquisitions (e.g. an MS² file) discover them at
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
    """Run a contract test once per reader backend (assessment Phase 5).

    Sets ``MASCOPE_THERMO_BACKEND`` for the test. The OpenTFRaw backend isn't
    implemented yet (migration step 4), so its runs are expected to xfail with
    ``NotImplementedError`` for now; as ``OpenTFRawBackend`` lands they flip to
    ``XPASS`` function by function (``strict=False`` keeps the suite green and
    surfaces the XPASS as the signal to promote them).

    Tests/fixtures that build per-test state by *calling* a backend function must
    depend on this fixture (directly or via an autouse setup fixture) so the env
    var is set before the call — a plain ``setup_method`` runs too early.
    """
    monkeypatch.setenv("MASCOPE_THERMO_BACKEND", request.param)
    if request.param == "opentfraw":
        request.applymarker(
            pytest.mark.xfail(
                reason="OpenTFRawBackend not implemented yet (migration step 4)",
                raises=NotImplementedError,
                strict=False,
            )
        )
    return request.param


def read_or_xfail(fn, *args, **kwargs):
    """Call a backend read inside *fixture setup*, turning a not-yet-implemented
    backend into an xfail.

    The ``backend`` fixture's ``xfail(raises=NotImplementedError)`` only covers a
    test's *call* phase; an exception during fixture setup is otherwise reported
    as an error. An imperative ``pytest.xfail()`` works in setup, and — since it
    only fires when the call actually raises — the test still runs (and XPASSes)
    once the backend is implemented.
    """
    try:
        return fn(*args, **kwargs)
    except NotImplementedError as exc:
        pytest.xfail(str(exc))
