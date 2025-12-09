import numpy as np
from mascope_tools.alignment.calibration import CentroidedSpectrum, Spectra


def test_compute_sum_spectrum_basic():
    """Test the basic functionality of compute_sum_spectrum."""
    n_points = 2
    spectrum1 = CentroidedSpectrum(
        mz=np.array([1, 20], dtype=np.float64),
        intensity=np.ones(n_points, dtype=np.float64) * 100,
        resolution=np.ones(n_points, dtype=np.float64),
        signal_to_noise=np.ones(n_points, dtype=np.float64) * 5,
        peak_id=np.arange(1, n_points + 1, dtype=int),
    )
    spectrum2 = CentroidedSpectrum(
        mz=np.array([2, 21], dtype=np.float64),
        intensity=np.ones(n_points, dtype=np.float64) * 100,
        resolution=np.ones(n_points, dtype=np.float64),
        signal_to_noise=np.ones(n_points, dtype=np.float64) * 5,
        peak_id=np.arange(1, n_points + 1, dtype=int) * 10,
    )

    spectra = Spectra([spectrum1, spectrum2], timestamps=[0, 1])
    sum_spectrum = spectra.compute_sum_spectrum(average=True)

    expected_mz = np.array([1.5, 20.5], dtype=np.float64)
    expected_intensity = np.array([100, 100], dtype=np.float64)
    expected_peak_id = np.array([list([1, 10]), list([2, 20])], dtype=object)

    assert np.array_equal(
        sum_spectrum.mz, expected_mz
    ), f"{sum_spectrum.mz} m/z values do not match expected {expected_mz}"
    assert np.array_equal(
        sum_spectrum.intensity, expected_intensity
    ), f"{sum_spectrum.intensity} intensity values do not match expected {expected_intensity}"

    # Peak ID must be compared element-wise due to being arrays of arrays
    for actual, expected in zip(sum_spectrum.peak_id, expected_peak_id):
        assert list(actual) == list(
            expected
        ), f"{actual} peak ID does not match expected {expected}"
