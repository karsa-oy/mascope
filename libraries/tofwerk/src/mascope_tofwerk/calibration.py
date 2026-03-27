import numpy as np
from scipy.optimize import fsolve, least_squares


def mz_calibrate(peak_tof, peak_mz, exact_mz):
    """
    Calibrate m/z values using known peak positions and exact m/z values.

    :param peak_tof: Array of observed time-of-flight (TOF) values for calibration peaks.
    :type peak_tof: array-like
    :param peak_mz: Array of observed m/z values for calibration peaks.
    :type peak_mz: array-like
    :param exact_mz: Array of exact m/z values for calibration peaks.
    :type exact_mz: array-like
    :raise ValueError: If fewer than two calibration points are provided.
    :raise ValueError: If the calibration optimization fails.
    :return: Tuple containing the mass calibration parameters and calibration statistics.
    :rtype: tuple(dict, dict)
    """
    peak_tof = np.asarray(peak_tof, dtype=np.float64)
    peak_mz = np.asarray(peak_mz, dtype=np.float64)
    exact_mz = np.asarray(exact_mz, dtype=np.float64)

    if peak_tof.shape[0] < 2:
        raise ValueError("At least two calibration points are required for mode 0.")

    def residuals(par: np.ndarray, m: np.ndarray, tof: np.ndarray) -> np.ndarray:
        return par[0] * np.sqrt(m) + par[1] - tof

    # Initial guess: linear fit between sqrt(m) and tof
    X = np.vstack([np.sqrt(exact_mz), np.ones_like(exact_mz)]).T
    p_init, _, _, _ = np.linalg.lstsq(X, peak_tof, rcond=None)

    result = least_squares(
        residuals,
        x0=p_init,
        args=(exact_mz, peak_tof),
        method="trf",
        loss="soft_l1",
        max_nfev=1000,
    )

    if not result.success:
        raise ValueError(f"Calibration failed: {result.message}")

    calibration_parameters = result.x

    mz_calibration_result = {
        "mode": 0,
        "par": calibration_parameters.tolist(),
    }

    # Calculate new m/z for each TOF using the calibration
    new_peak_mz = tof_to_mass(peak_tof, mode=0, par=calibration_parameters)

    delta_mass_before_calibration = (peak_mz - exact_mz) / exact_mz * 1e6
    delta_mass_after_calibration = (new_peak_mz - exact_mz) / exact_mz * 1e6

    stats = {
        "mz": exact_mz,
        "new_mz": new_peak_mz,
        "pre_dmz": delta_mass_before_calibration,
        "post_dmz": delta_mass_after_calibration,
    }

    return mz_calibration_result, stats


def tof_to_mass(tof: np.ndarray, mode: int, par: list) -> float | np.ndarray:
    """Convert between sample indices and mass.

    :param tof: Values to convert
    :type tof: np.ndarray
    :param mode: Mass calibration function to use
    :type mode: int
    :param par: List containing the calibration parameters (number depends on mode)
    :type par: list
    """

    def solve_numerically(objective, tof_val):
        m_initial_guess = 1.0
        (m_solution,) = fsolve(objective, m_initial_guess, args=(tof_val,))
        return m_solution

    match mode:
        case 0:
            # from i(m) = p1 * np.sqrt(m) + p2
            return ((tof - par[1]) / par[0]) ** 2
        case 1:
            # from i(m) = p1/np.sqrt(m) + p2
            return (par[0] / (tof - par[1])) ** 2
        case 2:
            # from i(m) = p1 * np.power(m, p3) + p2
            return ((tof - par[1]) / par[0]) ** (1 / par[2])
        case 3:
            objective = (
                lambda m, tof_val: par[0] * np.sqrt(m)
                + par[1]
                + par[2] * (m - par[3]) ** 2
                - tof_val
            )
            return np.vectorize(lambda tof_val: solve_numerically(objective, tof_val))(
                tof
            )
        case 4:
            objective = (
                lambda m, tof_val: par[0] * np.sqrt(m)
                + par[1]
                + par[2] * m**2
                + par[3] * m
                + par[4]
                - tof_val
            )
            return np.vectorize(lambda tof_val: solve_numerically(objective, tof_val))(
                tof
            )
        case 5:
            return par[0] * tof**2 + par[1] * tof + par[2]
        case _:
            raise ValueError(f"Unknown mass calibration mode: {mode}")
