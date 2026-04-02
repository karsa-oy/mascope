import os
import shutil
import warnings
from glob import glob

import numpy as np
import xarray as xarr
from scipy.stats import norm, skewnorm
from test_utils.dataset_generator import GenerationParams, SpectraGenerator

from mascope_backend.runtime import runtime
from mascope_signal.peak import fit_n_peaks, segment_spec


warnings.filterwarnings("ignore")


def min_max_scaling(array):
    """Scales a NumPy array to the range 0-1."""
    min_val = np.min(array)
    max_val = np.max(array)
    return (array - min_val) / (max_val - min_val)


def find_closest_indices(detected, ground_truth):
    """
    Finds the closest indices of values from 'detected' in 'ground_truth'.

    Parameters:
    detected (np.array): Array of detected values.
    ground_truth (np.array): Array of ground truth values.

    Returns:
    np.array: Array of indices in 'ground_truth' that are closest to each value in 'detected'.
    """
    # Create an array to hold the indices of the closest values
    detected = np.asarray(detected)
    closest_indices = np.zeros_like(detected, dtype=int)

    for i, value in enumerate(detected):
        # Find the index of the closest value in ground_truth
        closest_index = np.abs(ground_truth - value).argmin()
        closest_indices[i] = closest_index

    return closest_indices


def generate_peak_shape(ms, x=None, scale=1, a=2):
    """Generate peak shape as dict"""
    if x is None:
        x = np.arange(-100, 100)
    match ms:
        case "orbi":
            y = norm.pdf(x, scale=scale)
        case "tof":
            y = skewnorm.pdf(x, scale=scale, a=a)
        case _:
            raise ValueError("Unknown mass spectrometer. Choose orbi or tof.")
    peak_shape = {"x": x, "y": y}
    return peak_shape


def res_fun_orbi(mz, a=1.715e6):
    """Compute Orbitrap resolution function"""
    return a / np.sqrt(mz)


def res_fun_tof(mz, a=1e-4, b=1e-3):
    """Compute TOF resolution function"""
    return mz / (a * mz + b)


def create_temp_folder(folder_name="temp"):
    """Create temp folder to store temp files, such as artificial spectra

    Return
        path to the created temp folder
    """
    # Get path to filestore
    # Recreate path to the temp folder
    temp_path = runtime.filestore(folder_name)

    # Delete old temp folder if it still exists
    if os.path.exists(temp_path):
        shutil.rmtree(temp_path)

    # Make temp folder
    os.makedirs(temp_path)

    return temp_path


def test_peak_fitting():
    """Test peak fitting performance"""
    temp_path = create_temp_folder()
    runtime.logger.info("Temp folder was created")

    # Set artificial spectra generation parameters
    tof_params = GenerationParams("tof", n_peaks=20)
    orbi_params = GenerationParams("orbi", n_peaks=20)

    # Init spectra generators
    tof_generator = SpectraGenerator(tof_params)
    orbi_generator = SpectraGenerator(orbi_params)
    runtime.logger.info("Generation parameters set. Generating spectra...")

    # Generate several spectra for each MS type
    for _ in range(1):
        # Generate spectra
        tof_generator.generate_spec()
        orbi_generator.generate_spec()

        # Save to zarr
        tof_generator.to_zarr(path=temp_path)
        orbi_generator.to_zarr(path=temp_path)

    runtime.logger.info("Spectra were generated. Performing peak fitting...")

    for file_path in glob(os.path.join(temp_path, "*")):
        runtime.logger.info(f"File {file_path}:")

        zarr_file = xarr.open_zarr(file_path)

        # Get spectrum and mz scale
        spec = zarr_file.sum_signal.values
        mz = zarr_file.sum_signal.mz.values

        if zarr_file.attrs["ms_type"] == "orbi":
            # Segment artificial spectrum
            segmented_indices = segment_spec(spec)
            specs_to_fit = [(mz[chunk], spec[chunk]) for chunk in segmented_indices]
            res_fun = res_fun_orbi
        if zarr_file.attrs["ms_type"] == "tof":
            dmz = 0.5
            u_list = np.arange(
                min(zarr_file.attrs["mz_range"]), max(zarr_file.attrs["mz_range"]) + 1
            )
            specs_to_fit = [
                (
                    mz[np.logical_and(mz >= u - dmz, mz <= u + dmz)],
                    spec[np.logical_and(mz >= u - dmz, mz <= u + dmz)],
                )
                for u in u_list
            ]
            res_fun = res_fun_tof

        fitted_peaks = []
        r_squared = []
        for mz_chunk, spec_chunk in specs_to_fit:
            fit, fitted_chunk = fit_n_peaks(
                mz_chunk,
                spec_chunk,
                generate_peak_shape(zarr_file.attrs["ms_type"]),
                res_fun,
                0.9,
            )
            if fit is None:
                # Nothing to fit
                continue

            # Calculate error
            spec_fitted = fit.residual + spec_chunk
            ss_res = np.sum(fit.residual**2)
            ss_tot = np.sum((spec_fitted - np.mean(spec_fitted)) ** 2)
            r_squared_val = 1 - (ss_res / ss_tot)
            for i in fitted_chunk:
                fitted_peaks.append(i)
                r_squared.append(r_squared_val)

        runtime.logger.info(
            f"Mean R-squared during the fitting was {np.mean(r_squared):.2f}"
        )

        # Convert fitted peaks to numpy array
        fitted_peaks = np.asarray(fitted_peaks)
        # Get fitted peak positions and heights
        fitted_pos = fitted_peaks[:, 0]
        fitted_hei = fitted_peaks[:, 1]

        # True values
        true_pos = zarr_file.true_peak_heis.dropna(dim="mz").mz.values
        true_hei = zarr_file.true_peak_heis.dropna(dim="mz").values

        # Calculate the error for each prediction
        error_ppm = 1
        errors = np.abs(np.subtract.outer(true_pos, fitted_pos))
        min_errors = np.min(errors, axis=1) / true_pos * 10**6

        runtime.logger.warning(
            f"{len(min_errors[min_errors > error_ppm])} peaks are off by more than {error_ppm} ppm"
        )

        # TODO decide if we want to continue with ROC curve and AUC
        # TODO false detections should be included in AUC score
        # TODO Oskari:"come up with some clever "score" in [0, 1] for the peaks
        # TODO which somehow represents their significance from the fitting algorithm point of view"
        # binary_labels = (min_errors <= error_ppm).astype(int)
        # # Calculate sort of probabilities
        # errors_proba = error_ppm - min_errors
        # # We are sure about 0 labeled peaks
        # errors_proba[errors_proba < 0] = 1
        # # Min-max normalization
        # errors_proba[errors_proba >= 0] = min_max_scaling(
        #     errors_proba[errors_proba >= 0]
        # )
        # # Determine binary labels based on the 1 ppm error threshold
        # binary_labels = (min_errors <= error_ppm).astype(int)

        # try:
        #     roc_auc = roc_auc_score(binary_labels, errors_proba)
        #     runtime.logger.info("AUC score is %.2f", roc_auc)
        # except ValueError:
        #     runtime.logger.info(
        #         "AUC score was not estimated, all fitted peaks within %.2f ppm error",
        #         error_ppm,
        #     )

        if len(fitted_pos) != len(true_pos):
            runtime.logger.warning(
                f"{len(true_pos)} peaks expected but {len(fitted_pos)} found!"
            )

            # undectection
            if len(true_pos) > len(fitted_pos):
                close_pos_inds = find_closest_indices(fitted_pos, true_pos)
                diff_mask = np.ones(true_hei.shape, dtype=bool)
                diff_mask[close_pos_inds] = False
                diff_peaks = true_hei[diff_mask]
            # overdetection
            else:
                close_pos_inds = find_closest_indices(true_pos, fitted_pos)
                diff_mask = np.ones(fitted_hei.shape, dtype=bool)
                diff_mask[close_pos_inds] = False
                diff_peaks = fitted_hei[diff_mask]

            runtime.logger.warning(
                f"""
                Undetected/excessive peak heights:
                    min={np.min(diff_peaks):.2e}
                    mean={np.mean(diff_peaks):.2e}
                    max={np.max(diff_peaks):.2e}
                """
            )
