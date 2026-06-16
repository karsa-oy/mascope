"""End-to-end parity for the instrument resolution fit across reader backends.

This is the *true* acceptance for the OpenTFRaw `average_profile` reimplementation
(migration T1a): the instrument-function fit reads the summed profile and derives
a resolution function from per-peak FWHM. Here we run the real fit internals
(`_process_peak_shapes` + `_fit_resolution_function`) on the sum signal produced
by each backend and assert the fitted Orbitrap resolution coefficient agrees.

Lives in `mascope_signal` (not `mascope_thermo`) because the fit lives here and
`mascope_signal` depends on `mascope_thermo` (not the other way round). Uses the
shared `mascope_thermo` `.raw` corpus; only the committed 2-scan KORBI files ship
in CI (too few peaks for a fit), so this skips there and exercises on the larger
local acquisitions on a dev machine.
"""

from pathlib import Path

import numpy as np
import pytest

opentfraw = pytest.importorskip("opentfraw")

import mascope_thermo.thermo as m_thermo  # noqa: E402
from mascope_signal.instrument_func.fit import (  # noqa: E402
    _fit_resolution_function,
    _process_peak_shapes,
)

# mascope_thermo's test corpus (shared); resolves relative to this file.
TEST_FILES_DIR = Path(__file__).resolve().parents[2] / "thermo" / "tests" / "test_files"
RAW_FILES = sorted(TEST_FILES_DIR.glob("*.raw"))

# The OpenTFRaw profile accessor (and the average_profile path) is only present
# in a maturin build of the accessor branch, not the published wheel.
_OTF_HAS_PROFILE = hasattr(opentfraw.RawFile, "profile")

MAX_SCANS = 40  # bound the averaging window for test runtime


def _bounded_window(path):
    import os

    os.environ["MASCOPE_THERMO_BACKEND"] = "thermo"
    times = np.sort(m_thermo.get_scan_timestamps(path))
    if times.size == 0:
        return None, None
    return float(times[0]), float(times[min(times.size, MAX_SCANS) - 1])


def _fit_resolution_coeff(path, backend, t_min, t_max):
    """Orbitrap resolution coefficient `a` (R = a/sqrt(m)) fitted from the
    backend's sum signal, or None if there are too few quality peaks."""
    import os

    os.environ["MASCOPE_THERMO_BACKEND"] = backend
    sig, _ = m_thermo.compute_sum_signal(path, t_min=t_min, t_max=t_max)
    mz = np.asarray(sig.mz.values, dtype=float)
    spec = np.asarray(sig.values, dtype=float)
    try:
        _, _, p_mzs, p_fwhms = _process_peak_shapes(
            mz, spec, "orbitrap", dmz=0.5, r_sq_thres=0.95
        )
    except ValueError:
        return None  # "Not enough quality peaks"
    if len(p_mzs) < 3:
        return None
    resolution_function, _ = _fit_resolution_function("orbitrap", p_mzs, p_fwhms)
    return float(resolution_function.keywords["a"])


@pytest.mark.skipif(
    not _OTF_HAS_PROFILE,
    reason="installed opentfraw lacks RawFile.profile() (needs the accessor build)",
)
@pytest.mark.skipif(not RAW_FILES, reason="no .raw files in the thermo test corpus")
@pytest.mark.parametrize("path", RAW_FILES, ids=lambda p: p.name)
def test_resolution_fit_matches_thermo(path):
    """The Orbitrap resolution coefficient fitted from OpenTFRaw's sum signal
    must match the one fitted from Thermo's, to within a few percent (the fit
    follows directly from per-peak FWHM, which average_profile reproduces)."""
    path = str(path)
    t_min, t_max = _bounded_window(path)

    a_thermo = _fit_resolution_coeff(path, "thermo", t_min, t_max)
    if a_thermo is None:
        pytest.skip("Thermo sum signal has too few quality peaks to fit")
    a_otf = _fit_resolution_coeff(path, "opentfraw", t_min, t_max)
    if a_otf is None:
        pytest.skip("OpenTFRaw sum signal has too few quality peaks to fit")

    # The Orbitrap fit uses only a handful of quality peaks, so the coefficient
    # is inherently a bit noisy; ~10% catches gross regressions (e.g. the
    # binning bug that gave a ~0.6 FWHM ratio) while tolerating peak-selection
    # differences. Measured ~0.95 on a Q Exactive Plus file.
    assert a_otf == pytest.approx(a_thermo, rel=0.1), (
        f"resolution coeff a: OpenTFRaw {a_otf:.4g} vs Thermo {a_thermo:.4g}"
    )
