import numpy as np
from scipy.optimize import fsolve
from mascope_tofwerk.lib.TwTool import TwMassCalibrate


def mz_calibrate(peak_tof, peak_mz, exact_mz):
    """
    Calibrate m/z values using known peak positions and exact m/z values.

    :param peak_tof: Array of observed time-of-flight (TOF) values for calibration peaks.
    :type peak_tof: array-like
    :param peak_mz: Array of observed m/z values for calibration peaks.
    :type peak_mz: array-like
    :param exact_mz: Array of exact m/z values for calibration peaks.
    :type exact_mz: array-like
    :raises Exception: If TwMassCalibrate fails.
    :return: Tuple containing the mass calibration parameters and calibration statistics.
    :rtype: tuple(dict, dict)
    """
    calibration_mode = 0
    nbr_points = len(peak_tof)
    mass = np.array(exact_mz, dtype=np.double)
    tofs = np.array(peak_tof, dtype=np.double)
    peak_mz = np.array(peak_mz)
    weight = np.ones((nbr_points,))  # TODO: Set weights?
    nbr_params = np.array([2], dtype=int)
    calibration_parameters = np.zeros((nbr_params[0],), dtype=np.double)
    legacy_a = legacy_b = np.array([None], dtype=np.double)

    ret = TwMassCalibrate(
        calibration_mode,
        nbr_points,
        mass,
        tofs,
        weight,
        nbr_params,
        calibration_parameters,
        legacy_a,
        legacy_b,
    )

    if ret != 4:
        raise Exception(f"TwMassCalibrate failed with code: {ret}")

    mz_calibration_result = {
        "mode": calibration_mode,
        "par": list(calibration_parameters),
    }

    new_peak_mz = np.array(
        [tof_to_mass(tof, calibration_mode, calibration_parameters) for tof in tofs]
    )
    delta_mass_before_calibration = (peak_mz - mass) / mass * 1e6
    delta_mass_after_calibration = (new_peak_mz - mass) / mass * 1e6

    stats = {
        "mz": mass,
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
