"""Cross-backend numerical parity for reimplemented computed ops.

Where OpenTFRaw needs a NumPy reimplementation of a Thermo-computed operation
(assessment gaps 5.3 / 5.4), the dual-backend contract suite only checks the
*shape* of the result. These tests pin the *values*: run the same public
function under both backends and assert agreement. This is the evidence that a
reimplementation actually reproduces Thermo's numbers, not just its structure.

Both backends (pythonnet + opentfraw) are runtime dependencies of
``mascope_thermo``, so they're assumed importable (as in the other tests).
"""

import numpy as np
import pytest
from conftest import NEG_ORBI_FILE_PATH, POS_ORBI_FILE_PATH

import mascope_thermo.thermo as m_thermo


def _run_under(monkeypatch, backend, fn, *args, **kwargs):
    monkeypatch.setenv("MASCOPE_THERMO_BACKEND", backend)
    return fn(*args, **kwargs)


@pytest.mark.parametrize(
    "path, polarity",
    [(POS_ORBI_FILE_PATH, "+"), (NEG_ORBI_FILE_PATH, "-")],
)
def test_xic_matches_thermo(monkeypatch, path, polarity):
    """OpenTFRaw's NumPy XIC must reproduce Thermo's MassRange chromatogram.

    Targets are the most intense real centroids in the file, so the windows
    actually contain signal.
    """
    monkeypatch.setenv("MASCOPE_THERMO_BACKEND", "thermo")
    masses, intensities, _, _ = m_thermo.get_centroids(path, polarity=polarity)
    if masses.size == 0:
        pytest.skip("no centroids to target")
    targets = np.sort(masses[np.argsort(intensities)[::-1][:8]])

    thermo_xic = _run_under(
        monkeypatch,
        "thermo",
        m_thermo.get_peak_timeseries,
        path,
        targets,
        polarity=polarity,
    ).values
    otf_xic = _run_under(
        monkeypatch,
        "opentfraw",
        m_thermo.get_peak_timeseries,
        path,
        targets,
        polarity=polarity,
    ).values

    assert otf_xic.shape == thermo_xic.shape
    np.testing.assert_allclose(otf_xic, thermo_xic, rtol=1e-4, atol=1e-3)
