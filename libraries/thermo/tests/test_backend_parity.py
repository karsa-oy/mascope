"""Cross-backend numerical parity for reimplemented computed ops.

Where OpenTFRaw needs a NumPy reimplementation of a Thermo-computed operation
(assessment gaps 5.3 / 5.4), the dual-backend contract suite only checks the
*shape* of the result. These tests pin the *values*: run the same public
function under both backends and assert agreement. This is the evidence that a
reimplementation actually reproduces Thermo's numbers, not just its structure.

File-agnostic, like the parity harness: every ``*.raw`` in ``test_files/`` is
compared (only the KORBI files are committed; drop in more locally for wider
coverage). Both backends (pythonnet + opentfraw) are runtime dependencies of
``mascope_thermo``, so they're assumed importable.

Targets are sampled *evenly across the m/z range* rather than "all peaks": a
full Orbitrap file can have hundreds of thousands of averaged centroids, and
``get_peak_timeseries`` issues one Thermo ``GetChromatogramData`` trace per
target — so all-peaks is O(100k traces x scans) and takes tens of minutes. An
even spread (capped at ``MASCOPE_PARITY_MAX_XIC_TARGETS``, default 200) covers
the whole m/z range and varied peak densities in a second or two per file.
"""

import os

import numpy as np
import pytest
from conftest import TEST_FILES_DIR

import mascope_thermo.thermo as m_thermo


RAW_FILES = sorted(TEST_FILES_DIR.glob("*.raw"))

# Cap on XIC targets per file (even spread across m/z). Override to widen
# coverage (e.g. MASCOPE_PARITY_MAX_XIC_TARGETS=1000) at the cost of runtime.
MAX_XIC_TARGETS = int(os.environ.get("MASCOPE_PARITY_MAX_XIC_TARGETS", "200"))


def _run_under(monkeypatch, backend, fn, *args, **kwargs):
    monkeypatch.setenv("MASCOPE_THERMO_BACKEND", backend)
    return fn(*args, **kwargs)


@pytest.mark.skipif(not RAW_FILES, reason="no .raw files in test_files/")
@pytest.mark.parametrize("path", RAW_FILES, ids=lambda p: p.name)
def test_xic_matches_thermo(monkeypatch, path):
    """OpenTFRaw's NumPy XIC must reproduce Thermo's MassRange chromatogram for
    targets spanning the file's full m/z range, across all MS1 scans.
    """
    path = str(path)

    # Source real targets from the averaged centroids, then sample an even
    # spread across the sorted m/z range.
    monkeypatch.setenv("MASCOPE_THERMO_BACKEND", "thermo")
    masses, _, _, _ = m_thermo.get_centroids(path)
    if masses.size == 0:
        pytest.skip("no centroids to target")
    masses = np.sort(masses)
    idx = np.unique(
        np.linspace(0, masses.size - 1, min(MAX_XIC_TARGETS, masses.size)).astype(int)
    )
    targets = masses[idx]

    thermo_xic = _run_under(
        monkeypatch, "thermo", m_thermo.get_peak_timeseries, path, targets
    ).values
    otf_xic = _run_under(
        monkeypatch, "opentfraw", m_thermo.get_peak_timeseries, path, targets
    ).values

    assert otf_xic.shape == thermo_xic.shape
    np.testing.assert_allclose(otf_xic, thermo_xic, rtol=1e-4, atol=1e-3)
