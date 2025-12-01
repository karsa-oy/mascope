from typing import Iterable
import warnings
import numpy as np
import lmfit
from scipy.integrate import simpson
from scipy.spatial.distance import pdist


# Precompute sigma multiplier for peak generation
SIGMA_MULTIPLIER = 2 * np.sqrt(2 * np.log(2))

# Penalty factor for too close peaks
# The fitted region is normalized, so 1e3 is a reasonable value
PEAK_SEPARATION_PENALTY_FACTOR = 1e3


def fit_n_peaks(
    x: Iterable,
    y: Iterable,
    peak_shape: dict,
    resolution_function: callable,
    threshold: float,
    sample_interval: float = None,
    max_n_peaks: int = 5,
    fit_pos: bool = True,
    fit_hei: bool = True,
    fit_res: bool = False,
) -> tuple:
    """Fit a number of peaks to a signal.
    The function tries to fit a number of peaks to the signal 'y' using the
    specified peak shape and resolution function. It iteratively adds peaks
    until the residual norm does not decrease significantly.

    :param x: x-values of the signal (m/z values)
    :type x: Iterable
    :param y: y-values of the signal (intensity values)
    :type y: Iterable
    :param peak_shape: The shape of the peak to be fitted.
    :type peak_shape: dict
    :param resolution_function: A function that returns the resolution of the peak
    :type resolution_function: callable
    :param threshold: Threshold for adding a new peak.
    :type threshold: float
    :param sample_interval: signal sampling interval, defaults to None
    :type sample_interval: float, optional
    :param max_n_peaks: max number of peaks to fit, defaults to 5
    :type max_n_peaks: int, optional
    :param fit_pos: if vary peak positions, defaults to True
    :type fit_pos: bool, optional
    :param fit_hei: if vary peak heights, defaults to True
    :type fit_hei: bool, optional
    :param fit_res: if vary peak resolution, defaults to False
    :type fit_res: bool, optional
    :return: tuple containing the fit result, the fitted peaks, and caught warnings
    :rtype: tuple
    """
    if not len(y):
        return None, None, []

    # Convert peak shape
    peak_shape["x"] = np.array(peak_shape["x"], dtype=np.float64)
    peak_shape["y"] = np.array(peak_shape["y"], dtype=np.float64)

    spec_norm = np.linalg.norm(y)
    residual_norm = spec_norm
    prev_fit = None
    prev_peaks = []
    for i in range(max_n_peaks):
        if i == 0:
            # Initialize first peak
            max_ind = np.argmax(y)
            init_pos = [x[max_ind]]
            init_hei = [y[max_ind]]
            init_res = [
                (
                    resolution_function(x[max_ind])
                    if callable(resolution_function)
                    else resolution_function
                )
            ]

        dpos = None  # Set dpos to None to allow fitting within x range

        # Capture warnings during the fitting process
        captured_warnings = []
        with warnings.catch_warnings(record=True) as ws:
            warnings.simplefilter("always")
            fit, peaks = fit_peaks(
                x,
                y,
                peak_shape,
                i + 1,
                init_pos,
                init_hei,
                init_res,
                fit_pos,
                fit_hei,
                fit_res,
                dpos=dpos,
                max_iter=100,
            )
            captured_warnings.extend(str(w.message) for w in ws)

        if not fit:
            return None, [], []

        new_residual_norm = np.linalg.norm(fit.residual)
        # Check for add new peak condition
        if new_residual_norm > threshold * residual_norm:
            fit = prev_fit
            peaks = prev_peaks
            break
        residual_norm = new_residual_norm
        prev_fit = fit
        prev_peaks = peaks

        # --- Zero-out regions around already fitted peaks --- #
        peak_data = np.array(peaks)
        peak_positions = peak_data[:, 0]
        peak_resolutions = peak_data[:, 2]
        hwhms = (peak_positions / peak_resolutions) / 2
        x = np.asarray(x)
        # Vectorized mask, shape (n_peaks, len(x))
        peak_region_masks = (
            x[None, :] > (peak_positions[:, None] - hwhms[:, None])
        ) & (x[None, :] < (peak_positions[:, None] + hwhms[:, None]))
        total_peak_region_mask = np.any(peak_region_masks, axis=0)
        fit.residual[total_peak_region_mask] = 0

        # --- Set the position of next peak to the maximum of residual --- #
        max_residual_ind = np.argmax(fit.residual)
        max_residual = fit.residual[max_residual_ind]
        max_residual_mz = x[max_residual_ind]
        init_pos.append(max_residual_mz)
        init_hei.append(max_residual)
        init_res.append(
            resolution_function(max_residual_mz)
            if callable(resolution_function)
            else resolution_function
        )
    # Calculate peak areas
    peaks = [
        (*peak, calculate_peak_area(x, peak_shape, peak, sample_interval))
        for peak in peaks
    ]
    return fit, peaks, captured_warnings


def fit_peaks(
    x: np.ndarray,
    y: np.ndarray,
    ps: dict,
    npeaks: int,
    ppos: list,
    phei: list,
    pres: list,
    fit_pos: bool = True,
    fit_hei: bool = True,
    fit_res: bool = True,
    dpos: float = None,
    max_iter: int = 1000,
) -> tuple:
    """
    Fit a set of peaks to a signal.

    Tries to fit a set of peaks to the signal 'y', minimizing the reconstruction
    residual as defined in the function 'peak_kernel_residual'.

    :param x: Array of sample numbers.
    :type x: array-like
    :param y: Signal to be fitted.
    :type y: array-like
    :param ps: Peak shape.
    :type ps: dict
    :param npeaks: Number of peaks to fit.
    :type npeaks: int
    :param ppos: Initial guesses for peak positions, must have length 'npeaks'.
    :type ppos: list
    :param phei: Initial guesses for peak heights, must have length 'npeaks'.
    :type phei: list
    :param pres: Initial guesses for peak resolutions, must have length 'npeaks'.
    :type pres: list
    :param fit_pos: Whether to optimize peak positions, defaults to True.
    :type fit_pos: bool, optional
    :param fit_hei: Whether to optimize peak heights, defaults to True.
    :type fit_hei: bool, optional
    :param fit_res: Whether to optimize peak widths, defaults to True.
    :type fit_res: bool, optional
    :param dpos: Maximum allowed change in peak position during fitting, defaults to None.
    :type dpos: float, optional
    :param max_iter: Maximum number of minimizer iterations, defaults to 1000.
    :type max_iter: int, optional
    :return: Tuple containing the fit result and the fitted peaks.
    :rtype: tuple
    """

    # Normalize y
    ymax = y.max()
    if ymax == 0:
        return None, None
    yn = y / ymax
    # Initialize parameters
    params = lmfit.Parameters()
    params.add("npeaks", value=npeaks, vary=False)
    for p in range(npeaks):
        if dpos is not None:
            posmin = ppos[p] - dpos
            posmax = ppos[p] + dpos
        else:
            posmin = x[0]
            posmax = x[-1]
        params.add(f"peak{p}pos", value=ppos[p], min=posmin, max=posmax, vary=fit_pos)
        params.add(f"peak{p}hei", value=phei[p] / ymax, min=0, vary=fit_hei)
        params.add(f"peak{p}res", value=pres[p], min=0, vary=fit_res)
    # Check if number of varying parameters hit the limit
    num_of_params = npeaks * np.sum([fit_pos, fit_hei, fit_res])
    if num_of_params > len(x):
        return None, None
    # Fit
    minner = lmfit.Minimizer(
        peak_kernel_residual, params, fcn_args=(x, yn, ps), ftol=1e-6, xtol=1e-6
    )
    fit = minner.minimize(method="least_s", max_nfev=max_iter)
    # Rescale fit results
    fit.residual *= ymax
    for par in fit.params:
        if "hei" in par:
            fit.params[par].value *= ymax
            if fit.params[par].stderr is not None:
                fit.params[par].stderr *= ymax
    peaks = [
        (
            fit.params[f"peak{p}pos"].value,
            fit.params[f"peak{p}hei"].value,
            fit.params[f"peak{p}res"].value,
        )
        for p in range(npeaks)
    ]
    return fit, peaks


def gen_peak(
    x: np.ndarray,
    ppos: float,
    phei: float,
    pres: float,
    peak_shape: dict,
    trim_borders: bool = False,
) -> np.ndarray:
    """Generate a peak of specified height, width, and shape in the domain 'x'.

    :param x: Array of x-values where to generate the peak.
    :type x: np.ndarray
    :param ppos: Peak position (x-value).
    :type ppos: float
    :param phei: Peak height.
    :type phei: float
    :param pres: Peak resolution.
    :type pres: float
    :param peak_shape: Peak shape dictionary with keys 'x' and 'y'.
    :type peak_shape: dict
    :param trim_borders: If True, trim close-to-zero values from edges, defaults to False
    :type trim_borders: bool, optional
    :return: Array of peak values corresponding to input parameter 'x'.
             If trim_borders=True, returns a tuple (x_trimmed, peak_trimmed).
    :rtype: np.ndarray
    """
    sigma = ppos / pres / SIGMA_MULTIPLIER

    peak_shape["x"] = np.asarray(peak_shape["x"], dtype=np.float64)
    peak_shape["y"] = np.asarray(peak_shape["y"], dtype=np.float64)

    # Rescale peak shape
    xi = peak_shape["x"] * sigma + ppos
    yi = peak_shape["y"] / np.max(peak_shape["y"]) * phei

    # Interpolate to a new x scale
    peak = np.interp(x, xi, yi)

    peak = np.nan_to_num(peak, nan=0.0)
    peak[peak < 0] = 0

    if trim_borders:
        thr = 1e-5
        left_border_ind = np.argmax(peak >= thr)
        right_border_ind = np.argmax(peak[::-1] >= thr)
        right_border_ind = len(x) - right_border_ind if right_border_ind > 0 else -1
        return (
            x[left_border_ind:right_border_ind],
            peak[left_border_ind:right_border_ind],
        )

    return peak


def peak_kernel_residual(
    params: dict, x: np.ndarray, y: np.ndarray, peak_shape: dict
) -> np.ndarray:
    """Generate a kernel of peaks and calculate the residual with regards
    to 'y'. Objective function for the function 'fit_peaks'.

    If the peaks are too close, a penalty is added to the residuals.

    :param params: Parameters of peaks to be included in the kernel, in the format
        returned by the function 'fit_peaks'.
    :type params: dict
    :param x: Array of sample numbers for which to calculate the kernel.
    :type x: np.ndarray
    :param y: The signal regards to which the residual is to be calculated.
    :type y: np.ndarray
    :param peak_shape: Peak shape
    :type peak_shape: dict
    :return: The residual 'y - kernel'
    :rtype: np.ndarray
    """
    # Minimum distance between peaks to avoid fitting at the same position
    min_dist = np.min(np.diff(x)) * 0.5

    n_peaks = int(params["npeaks"].value)
    penalty = 0
    if n_peaks > 1:  # Only check for close peaks if there are at least 2 peaks
        # Extract current peak positions
        positions = np.array([params[f"peak{p}pos"].value for p in range(n_peaks)])
        # Calculate pairwise distances between peak positions
        position_diffs = pdist(positions.reshape(-1, 1))
        # Identify pairs of peaks that are too close
        close_peak_mask = position_diffs < min_dist
        # Compute penalty for residuals for each pair of too close peaks
        if np.any(close_peak_mask):
            penalty = (
                np.sum(min_dist - position_diffs[close_peak_mask])
                * PEAK_SEPARATION_PENALTY_FACTOR
            )

    # Compute residuals and add possible penalty
    kernel = gen_peak_kernel(params, x, peak_shape)
    residual = y - kernel + penalty

    return residual


def gen_peak_kernel(params: dict, x: np.ndarray, peak_shape: dict) -> np.ndarray:
    """Generate a kernel of peaks for the given parameters.

    :param params: Parameters of peaks to be included in the kernel, in the format
        returned by the function 'fit_peaks'.
    :type params: dict
    :param x: Array of sample numbers for which to calculate the kernel.
    :type x: np.ndarray
    :param peak_shape: Peak shape
    :type peak_shape: dict
    :return: Peak kernel in domain 'x'.
    :rtype: np.ndarray
    """
    npeaks = int(params["npeaks"].value)
    peaks = np.zeros((npeaks, len(x)))

    for p in range(npeaks):
        ppos = params[f"peak{p}pos"].value
        phei = params[f"peak{p}hei"].value
        pres = params[f"peak{p}res"].value
        peaks[p] = gen_peak(x, ppos, phei, pres, peak_shape)

    return np.sum(peaks, axis=0)


def calculate_peak_area(
    x: np.ndarray, peak_shape: dict, peak: tuple, sample_interval: float
) -> float:
    """Calculate the area of a peak.

    This function calculates the area under a peak shape using Simpson's rule.

    :param x: The array of x values corresponding to the peak.
    :type x: numpy.ndarray
    :param peak_shape: The median peak shape.
    :type peak_shape: dict
    :param peak: A tuple containing the position, height, and resolution of the peak.
    :type peak: tuple
    :return: The area under the peak shape.
    :rtype: float
    """
    pos, hei, res = peak
    peak_y = gen_peak(x, pos, hei, res, peak_shape)
    if sample_interval:
        # calculate peak area in TOF space
        return np.sum(peak_y) * sample_interval
    # calculate peak area in mz space
    return simpson(y=peak_y, x=x)
