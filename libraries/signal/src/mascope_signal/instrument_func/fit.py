from functools import partial
import asyncio
from argparse import ArgumentParser
import numpy as np
from scipy.signal import find_peaks
from scipy.stats import linregress
from scipy.optimize import curve_fit
from scipy.interpolate import interp1d
from lmfit.models import SplineModel, SkewedGaussianModel
from lmfit.model import ModelResult

from mascope_file.name import get_instrument_type
from mascope_file.io import load_array
from mascope_signal.compute import get_sum_signal

from mascope_signal.runtime import runtime


# Precompute sigma multiplier for peak generation
SIGMA_MULTIPLIER = 2 * np.sqrt(2 * np.log(2))
# Minimum number of peaks required to evaluate instrument functions
MIN_NUM_PEAKS = 3


async def fit_instrument_functions(filename: str, dmz=0.5, r_sq_thres=0.95) -> tuple:
    """Calculate instrument functions

    Compute the median peak shape from the normalized peak shapes (p_ys).
    Calculate the resolution function from pairs of peak positions (p_mzs) and FWHM (p_fwhms).

    Structure of the returned statistics:
    stats
        | peakshape
            | num_of_peaks: number of peak used for peakshape estimation
        | resolution_function
            | mz: m/z values of the peak used to fit resolution function
            | fwhm: widths of the peak used to fit resolution function

    :param filename: Sample file name
    :type filename: str
    :param dmz: m/z window width for peak selection, defaults to 0.5
    :type dmz: float, optional
    :param r_sq_thres: R-squared threshold for peak fitting, defaults to 0.95
    :type r_sq_thres: float, optional
    :raises ValueError: Not enough peaks for instrument function estimation
    :return: Tuple containing the peak shape as dict, resolution function as partial, statistics as dict
    :rtype: tuple
    """
    instrument_type = get_instrument_type(filename)

    sum_signal = get_sum_signal(filename)
    spec = sum_signal.values
    mz = sum_signal.mz.values

    # Get x-domain, normalized peak shapes and associated peak positions and FWHMs
    p_x, p_ys, p_mzs, p_fwhms = await process_peak_shapes(
        mz, spec, instrument_type, dmz, r_sq_thres
    )
    # Check if there are enough peaks for peak shape estimation
    if len(p_mzs) < MIN_NUM_PEAKS:
        error_message = "Not enough quality peaks to evaluate instrument functions"
        runtime.logger.error(error_message)
        raise ValueError(error_message)

    peak_shape, ps_stats = calculate_peakshape(p_x, p_ys)
    resolution_function, resfun_stats = await fit_resolution_function(
        instrument_type, p_mzs, p_fwhms
    )

    # Merge peakshape and resolution function statistics
    stats = ps_stats | resfun_stats

    return peak_shape, resolution_function, stats


async def process_peak_shapes(
    mz: np.ndarray,
    spec: np.ndarray,
    instrument_type: str,
    dmz: float,
    r_sq_thres: float,
    n_peaks=50,
) -> tuple:
    """Calculate normalized peak shapes and their parameters from a given spectrum

    1. Find indices of the potential peaks in the spectrum.
    2. Pick several peaks (50 by default) with the highest intensity.
    3. Predefine the common domain/x-scale for the peaks.
    4. Process each peak:
        a) Select and normalize narrow regions around the peak.
        b) Fit skewed Gaussian (+ baseline in case of TOF) in the region.
        c) Drop the peak if the fitting error exceeds a threshold.
        d) Extract fitted peak parameters: center, full-width half maximum (FWHM), sigma, height.
        e) Normalize peak region by these parameters.
        f) Interpolate the region into the predefined domain.
        g) Store refined peak shape (p_ys), raw (p_mzs) and fitted peak positions, fitted peak FWHM (p_fwhms).
    5. Filter out p_ys with centers of mass too far from median values among all peak shapes.

    :param mz: Spectrum m/z values
    :type mz: np.ndarray
    :param spec: Spectrum counts / intensity
    :type spec: np.ndarray
    :param instrument_type: Spectrometer type, tof or orbi
    :type instrument_type: str
    :param dmz: m/z window width for peak selection
    :type dmz: float
    :param r_sq_thres: R-squared threshold for peak fitting
    :type r_sq_thres: float
    :param n_peaks: Number of peaks with the highest intensity used in calculations, defaults to 100
    :type n_peaks: int
    :return: Tuple containing p_x, p_ys, p_mzs, and p_fwhms
    :rtype: tuple
    """
    distance = int(dmz / np.median(np.diff(mz)))
    peak_indices = choose_peaks(spec, distance=distance, n_peaks=n_peaks)

    p_x = np.linspace(-10, 10, 101)
    p_ys, p_mzs, p_fwhms, p_centers = [], [], [], []

    for p in peak_indices:
        p_mz_center = mz[p]

        # Select a narrow region (peak center +/- dmz) of the spectrum around the peak
        region_mask = np.where((mz > p_mz_center - dmz) & (mz < p_mz_center + dmz))
        p_spec = spec[region_mask]
        p_mz = mz[region_mask]

        p_height = spec[p]
        if np.max(p_spec) > p_height:
            # 'p' is not the biggest peak in range, dismiss
            continue

        # Normalize peak region: mz around 0 and spec to range [0, 1]
        p_mz_norm = p_mz - p_mz_center
        p_spec_norm = p_spec / p_height

        # Fit peak in the region
        fit = fit_gaussian(instrument_type, dmz, p_mz_norm, p_spec_norm)
        p_spec_norm_fit = fit.eval_components()["p_"]

        if fit.rsquared < r_sq_thres:
            # fitting error too large, dismiss
            continue

        # Remove junk peaks arond main one
        noise_mask = np.where(fit.best_fit < 1e-9)
        p_spec_norm[noise_mask] = 0

        # Get peak top location
        if instrument_type == "tof":
            # Remove baseline if TOF
            p_spec_norm -= fit.eval_components()["bkg_"]
            p_spec_norm[np.where(p_spec_norm < 0)] = 0

        top_y = np.max(p_spec_norm_fit)
        top_x = calculate_center_of_mass(p_mz_norm, p_spec_norm_fit)

        # Get and store Gaussian peak sigma and width
        try:
            p_fwhm = calculate_fwhm(p_mz_norm, p_spec_norm_fit)
            p_sigma = p_fwhm / SIGMA_MULTIPLIER
        except Exception:
            continue

        # Scale peak to width sigma=1
        p_mz_norm /= p_sigma
        # Refine peak position and height
        p_mz_norm -= top_x
        p_spec_norm /= top_y

        # Interpolate the normalized (both width and height) peak into predefined domain "p_x"
        p_y = np.interp(p_x, p_mz_norm, p_spec_norm, left=0, right=0)

        if np.all(np.isnan(p_y)):
            continue

        # Store peak positions, widths, and refined peak shape
        p_mzs.append(p_mz_center)
        p_centers.append(top_x)
        p_fwhms.append(p_fwhm)
        p_ys.append(p_y)

    # Clean shifted outliers
    p_centers = np.array(p_centers)
    center_mad = np.median(np.abs(p_centers - np.median(p_centers)))
    non_outlier_mask = np.where(
        np.abs(p_centers - np.median(p_centers)) < 3 * center_mad
    )[0]

    p_fwhms = [p_fwhms[i] for i in non_outlier_mask]
    p_ys = [p_ys[i] for i in non_outlier_mask]
    p_mzs = [p_mzs[i] for i in non_outlier_mask]

    return p_x, p_ys, p_mzs, p_fwhms


def fit_gaussian(instrument_type, dmz, x: np.array, y: np.array) -> ModelResult:
    """Fit the spectrum range with a skewed Gaussian peak-shape using lmfit

    :param x: mz scale
    :type x: array-like
    :param y: counts
    :type y: array-like
    :return: ModelResult (see lmfit doc)
    :rtype: ModelResult
    """
    # Initialize fitting parameters for the main peak
    model = SkewedGaussianModel(prefix="p_")
    params = model.make_params()
    if instrument_type == "tof":
        # Fitting parameters for the background
        knot_xvals = np.array([-dmz, -dmz / 2, -dmz / 3, dmz / 3, dmz / 2, dmz])
        bkg = SplineModel(prefix="bkg_", xknots=knot_xvals)
        params.update(bkg.guess(y, x))
        # Total model
        model = model + bkg

    max_ind = np.argmax(y)
    params.add("p_amplitude", value=0.8 * y[max_ind], min=0, max=y[max_ind])
    params.add("p_center", value=x[max_ind], min=min(x), max=max(x))

    if instrument_type == "orbi":
        # Keep symmetric Gaussian
        params.add("p_gamma", value=0, vary=False)
        params.add("p_sigma", value=dmz / 5 / SIGMA_MULTIPLIER)
    if instrument_type == "tof":
        # Allow for slight skewed Gaussian
        params.add("p_gamma", value=0.1, min=0)
        params.add("p_sigma", value=0.01)

    fit = model.fit(y, params, x=x)
    return fit


def choose_peaks(spec: np.ndarray, distance: int, n_peaks=100) -> np.ndarray:
    """Select peaks from a spectrum based on a specified quartile threshold

    This function finds peaks in a given spectrum and returns n_peaks highest.

    :param spec: The spectrum data from which peaks are to be selected
    :type spec: np.ndarray
    :param distance: Required minimal horizontal distance (>= 1) in samples between
        neighbouring peaks.
    :type distance: int
    :param n_peaks: Number of peaks to return, defaults to 100
    :type n_peaks: int, optional
    :return: Array of indices where peaks are located in the spectrum
    :rtype: np.ndarray
    """
    peak_indices, _ = find_peaks(spec, distance=distance)

    # Extract the values at the peak indices
    peak_values = spec[peak_indices]

    # Sort the peak values in descending order and get the indices of the sorted values
    sorted_indices = np.argsort(peak_values)[::-1]

    # Select the top n_peaks highest peaks (or all if less than n_peaks)
    top_n_indices = sorted_indices[:n_peaks]

    # Get the corresponding peak indices in the original spectrum
    top_n_peak_indices = peak_indices[top_n_indices]

    return top_n_peak_indices


def calculate_center_of_mass(x: np.ndarray, y: np.ndarray) -> float:
    """Calculate the center of mass for given x and y values

    :param x: Array of x-values of the peak
    :type x: np.ndarray
    :param y: Array of y-values of the peak
    :type y: np.ndarray
    :return: The center of mass of the distribution
    :rtype: float
    """
    center_of_mass = np.sum(x * y) / np.sum(y)
    return center_of_mass


def calculate_fwhm(x: np.ndarray, y: np.ndarray) -> float:
    """Calculate FWHM of the peak

    :param x: Array of x-values of the peak
    :type x: np.ndarray
    :param y: Array of y-values of the peak
    :type y: np.ndarray
    :return: FWHM value
    :rtype: float
    """
    peak_index = np.argmax(y)
    peak_value = y[peak_index]

    half_max = peak_value / 2.0

    # Find indices where y crosses the half maximum
    indices_below = np.where(y[:peak_index] < half_max)[0]
    indices_above = np.where(y[peak_index:] < half_max)[0] + peak_index

    # Interpolate to find the exact crossing points
    if indices_below.size > 0 and indices_above.size > 0:
        f_left = interp1d(
            y[indices_below[-1] : peak_index + 1], x[indices_below[-1] : peak_index + 1]
        )
        f_right = interp1d(
            y[peak_index : indices_above[0] + 1],
            x[peak_index : indices_above[0] + 1],
            kind="slinear",
        )

        x_left = f_left(half_max)
        x_right = f_right(half_max)

        fwhm = x_right - x_left
    else:
        fwhm = None

    return fwhm


def calculate_peakshape(p_x: np.ndarray, p_ys: np.ndarray) -> tuple:
    """Calculate the meadian peak shape array from a 2D array of peaks

    :param p_x: array of normalized x-values corresponding to the peaks
    :type p_x: np.ndarray
    :param p_ys: 2D array where each row represents the y-values of a peak
    :type p_ys: np.ndarray
    :return: Tuple with dictionaries containing x and y values of the median peak shape and statistics
    :rtype: tuple
    """
    stats = {}
    num_of_peaks = len(p_ys)
    if num_of_peaks < 10:
        runtime.logger.warning(
            f"Only {num_of_peaks} peaks will be used to estimate median peak shape!"
        )
    else:
        runtime.logger.info(f"Peak shape will be averaged from {num_of_peaks} peaks")
    stats = {"num_of_peaks": num_of_peaks}

    # Calculate median peak shape
    p_median = np.median(np.array([p_y for p_y in p_ys]), axis=0)

    # Check if p_median is empty
    if p_median.all() == np.nan:
        runtime.logger.error("Median peak shape is empty")

    # Shift x-values so that the max y is at x=0
    max_index = np.argmax(p_median)
    x = p_x - p_x[max_index]

    # Normalize y-values to range from 0 to 1
    max_y = p_median[max_index]
    y = p_median / max_y

    # Normalize width
    fwhm = calculate_fwhm(x, y)
    sigma = fwhm / SIGMA_MULTIPLIER
    y /= sigma

    peak_shape = {"x": x, "y": y}
    return peak_shape, {"peakshape": stats}


async def fit_resolution_function(
    instrument_type: str, p_mzs: list | np.ndarray, p_fwhms: list | np.ndarray, ndev=1
) -> partial:
    """Calculate the resolution function for a given instrument type

    The function fits a resolution function based on the type of the instrument
    and the provided peak position in m/z and FWHM values. If the fit has failed,
    return the resolution function with default coefficients

    :param instrument_type: type of the instrument, tof or orbi
    :type instrument_type: str
    :param p_mzs: List or array of m/z values
    :type p_mzs: list | np.ndarray
    :param p_fwhms: List of FWHM values corresponding to the m/z values
    :type p_fwhms: list | np.ndarray
    :param ndev: Number of standard deviations used to filter out FWHM outliers
    :type ndev: int, optional
    :return: Resolution function as partial and dictionary with m/z and fitted FWHM lists
    :rtype: tuple
    """
    stats = {}
    p_mzs = np.array(p_mzs)
    p_fwhms = np.array(p_fwhms)

    # Fit FWHM vs m/z pairs
    p_fwhms_fit = fit_fwhm(instrument_type, p_mzs, p_fwhms)

    residuals = p_fwhms - p_fwhms_fit
    std_dev = np.std(residuals)
    if instrument_type == "tof":
        is_outlier = (residuals > 0) | (residuals < -ndev * std_dev)
    else:
        is_outlier = (residuals > ndev * std_dev) | (residuals < -ndev * std_dev)

    # Remove outliers
    p_fwhms_filt = np.array(p_fwhms)[~is_outlier]
    mass = np.array(p_mzs)[~is_outlier]

    resolution = mass / p_fwhms_filt

    stats["mz"] = mass.tolist()
    stats["fwhm"] = p_fwhms_filt.tolist()

    # Fit resolution function based on the instrument type
    try:
        if instrument_type == "tof":
            # TOF initial guesses
            a_init = 1 / np.mean(resolution)
            b_init = 1e2 * a_init
            bounds = ([0, 0], [1, np.inf])

            fit_res = curve_fit(
                rational_polynome,
                mass,
                resolution,
                p0=(a_init, b_init),
                bounds=bounds,
            )
            a, b = fit_res[0]
            resolution_function = partial(r_tof, a=a, b=b)
            runtime.logger.info(
                f"TOF resolution function coefficients: a={a:.2e}, b={b:.2e}"
            )

        else:
            fit_res = curve_fit(inverse_sqrt, mass, resolution)
            a = fit_res[0][0]
            resolution_function = partial(r_orbi, a=a)
            runtime.logger.info(f"Orbi resolution function coefficients: a={a:.2e}")

    except ValueError as e:
        runtime.logger.error(f"Resolution function fitting failed: {e}")
        raise ValueError("Resolution function fitting failed") from e

    return resolution_function, {"resolution_function": stats}


def fit_fwhm(
    instrument_type: str, p_mzs: np.ndarray, p_fwhms: np.ndarray
) -> np.ndarray:
    """Fit FWHM vs mz data points based on instrument type

    TOF data points are fitted with a line
    Orbi - with a 2nd order polynome

    :param instrument_type: type of the mass spectrometer
    :type instrument_type: str
    :param p_mzs: array of m/z values
    :type p_mzs: np.ndarray
    :param p_fwhms: azrray of FWHM values corresponding to p_mzs
    :type p_fwhms: np.ndarray
    :return: Fitted m/z values
    :rtype: np.ndarray
    """
    if instrument_type == "tof":
        regres = linregress(p_mzs, p_fwhms)
        p_fwhms_fit = line(p_mzs, regres.slope, regres.intercept)
    else:
        coefs = np.polyfit(p_mzs, p_fwhms, 2)
        p_fwhms_fit = polynome(p_mzs, *coefs)
    return p_fwhms_fit


def r_tof(mz: float | np.ndarray, a: float, b: float):
    """Calculate TOF resolution function

    :param mz: mz value(-s)
    :type mz: float or ndarray
    :param a: imperical coefficient
    :type a: float
    :param b: imperical coefficient
    :type b: float
    :return: resolution function value(-s)
    :rtype: float or ndarray
    """
    return mz / (a * mz + b)


def r_orbi(
    mz: float | np.ndarray,
    a: float,
):
    """Calculate Orbitrap resolution function

    :param mz: mz value(-s)
    :type mz: float or ndarray
    :param a: imperical coefficient
    :type a: float
    :return: resolution function value(-s)
    :rtype: float or ndarray
    """
    return a / np.sqrt(mz)


# Fitting support functions
def line(x, a, b):
    """Calculates the output of the linear function
    for given values of x (m/z), a (slope), and b (intercept)"""
    return a * x + b


def polynome(x, a, b, c):
    """Calculates the output of the 2nd order polynomial
    for given values of x, a, b, and c"""
    return a * x**2 + b * x + c


def rational_polynome(x, a, b):
    """Calculates the output of the rational polynome
    for given values of x, a, and b"""
    return x / (a * x + b)


def inverse_sqrt(x, a):
    """Calculates the output of the inverse square root
    for given values of x and a"""
    return a / np.sqrt(x)


if __name__ == "__main__":
    import dash
    from dash import dcc, html
    from dash.dependencies import Input, Output
    from mascope_signal.peak import detect_peaks
    from mascope_signal.inst_func_viz import vizualize, update_chosen_peak

    # Parse arguments
    parser = ArgumentParser()
    parser.add_argument(
        "-f", "--filename", dest="filename", help="Sample file name", required=True
    )
    parser.add_argument("-d", "--dmz", dest="dmz", help="Peak window size", default=0.5)
    parser.add_argument(
        "-r", "--r-squared", dest="r_sq_thres", help="R-squared threshold", default=0.96
    )
    args = parser.parse_args()

    # Calculate instrument functions
    try:
        instrument_type = get_instrument_type(args.filename)

        # Extract averaged spectrum and mz values
        sum_signal = get_sum_signal(args.filename)
        spec = sum_signal.values
        mz = sum_signal.mz.values

        # Get x-domain, normalized peak shapes and associated peak positions and FWHMs
        p_x, p_ys, p_mzs, p_fwhms = asyncio.run(
            process_peak_shapes(mz, spec, instrument_type, args.dmz, args.r_sq_thres)
        )
        p_mzs = np.array(p_mzs)
        p_fwhms = np.array(p_fwhms)

        # Get fitted FWHM vs m/z pairs
        p_fwhms_fit = fit_fwhm(instrument_type, p_mzs, p_fwhms)

        # Number of std to filter out outliers in FWHM fit
        ndev = 1

        ps, _ = calculate_peakshape(p_x, p_ys)
        res_fun, _ = asyncio.run(
            fit_resolution_function(instrument_type, p_mzs, p_fwhms, ndev)
        )

        # Fit peaks
        sample_file_data = asyncio.run(
            detect_peaks(
                args.filename,
                (ps, res_fun),
                0.9,
                u_list=p_mzs,
                if_exists="replace",
                dmz=args.dmz,
                instrument_type=instrument_type,
            )
        )
        sum_signal = get_sum_signal(args.filename)

        # Get fitted peak positions and heights
        fit_heis = (
            load_array(args.filename, "peak_heights")
            .dropna(dim="mz")
            .sum(dim="time")["peak_heights"]
        )
        fit_poss = fit_heis.mz.values
        fit_heis = fit_heis.values

        # Initialize the Dash app
        app = dash.Dash(__name__)

        # Get plotly figure
        fig = vizualize(p_mzs, p_fwhms, p_fwhms_fit, ndev, res_fun)

        # Define the layout of the Dash app
        app.layout = html.Div(
            [
                dcc.Graph(id="interactive-plot", figure=fig),
                html.Div(id="output"),
            ]
        )

        # Data to pass to callback
        data = {
            "fig": fig,
            "sum_signal": sum_signal,
            "fit_poss": fit_poss,
            "fit_heis": fit_heis,
            "res_fun": res_fun,
            "ps": ps,
        }

        # Define the callback to handle click events
        @app.callback(
            [Output("interactive-plot", "figure"), Output("output", "children")],
            [Input("interactive-plot", "clickData")],
        )
        def display_click_data(click_data):
            """Handles click event"""
            if click_data:
                points = click_data["points"][0]
                updated_fig = update_chosen_peak(points, **data)
                return updated_fig, f"Chosen mz = {points['x']:.2f}"
            return dash.no_update, "Click on a m/z data point in the plot"

        # Run Dash app
        app.run_server()

    except ValueError as err:
        runtime.logger.error("Check the filename")
        raise ValueError from err
