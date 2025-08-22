import os
import pickle
import mascope_sdk as msdk
import numpy as np
import pandas as pd
from .calibration import CentroidedSpectrum, Spectra
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mascope_jupyter_widgets import MascopeDataBrowser


def _is_notebook():
    try:
        from IPython import get_ipython

        shell = get_ipython().__class__.__name__
        return shell == "ZMQInteractiveShell"
    except Exception:
        return False


if _is_notebook():
    from tqdm.notebook import tqdm
else:
    from tqdm import tqdm


CACHE_FOLDER = os.path.abspath(os.path.join(os.getcwd(), "cached_spectra"))
# TODO increase chunk size after resolving the issue with blocked server
DOWNLOAD_CHUNK_SIZE = 1


def _cache_path(sample_item_id: str) -> str:
    return os.path.join(CACHE_FOLDER, str(sample_item_id))


def create_cache_folder():
    os.makedirs(CACHE_FOLDER, exist_ok=True)


def _save_cache(
    sample_item_id: str, spec_list: list[CentroidedSpectrum], timestamps: np.ndarray
) -> None:
    """Saves centroided spectra and timestamps to a cache file."""
    path = _cache_path(sample_item_id)
    tmp_path = path + ".__tmp__"
    with open(tmp_path, "wb") as f:
        pickle.dump(
            {
                "spectra": spec_list,
                "timestamps": np.asarray(timestamps, dtype=float),
            },
            f,
            protocol=pickle.HIGHEST_PROTOCOL,
        )
    os.replace(tmp_path, path)


def _load_cache(sample_item_id: str):
    """Loads cached centroided spectra and timestamps for a given sample_item_id."""
    path = _cache_path(sample_item_id)
    try:
        with open(path, "rb") as f:
            payload = pickle.load(f)
        return payload["spectra"], np.asarray(payload["timestamps"], dtype=float)
    except Exception:
        return None


def ppm_to_da(mz0: float, ppm: float) -> float:
    return mz0 * ppm * 1e-6


def collect_spectra(
    data_browser: "MascopeDataBrowser",
    samples: pd.DataFrame,
    update_cached: bool = False,
) -> Spectra:
    """
    Collects centroided spectra and their corresponding timestamps from a set of samples.

    :param data_browser: MascopeDataBrowser instance for accessing Mascope data.
    :type data_browser: MascopeDataBrowser
    :param samples: DataFrame containing sample metadata, must include 'datetime', 'sample_file_id', and 'polarity' columns.
    :type samples: pd.DataFrame
    :param update_cached: If True, will update the cache with new spectra, defaults to False.
    :type update_cached: bool, optional
    :return: Spectra object containing the collected centroided spectra and their timestamps.
    :rtype: Spectra
    """
    create_cache_folder()

    samples = samples.sort_values("datetime").reset_index(drop=True)
    cached_sample_item_ids = set(os.listdir(CACHE_FOLDER))

    time_since_first_sample_s = (
        (samples.datetime - samples.datetime[0]).dt.total_seconds().values
    )
    sample_item_ids = samples.sample_item_id.values.tolist()

    # Decide which IDs to fetch vs load based on cache state and update flag
    if update_cached:
        to_fetch = sample_item_ids
        to_load = []
    else:
        to_fetch = [sid for sid in sample_item_ids if sid not in cached_sample_item_ids]
        to_load = [sid for sid in sample_item_ids if sid in cached_sample_item_ids]

    # Collect all data (per sample_item_id) into a dict
    per_sample_data = {}

    # Load from cache
    for sid in tqdm(to_load, desc="Loading centroided spectra from cache"):
        loaded = _load_cache(sid)
        if loaded is None:
            # Corrupted/missing file -> re-fetch this one
            to_fetch.append(sid)
        else:
            per_sample_data[sid] = loaded

    # Fetch missing (or all, if update_cached)
    if to_fetch:
        num_chunks = (len(to_fetch) + DOWNLOAD_CHUNK_SIZE - 1) // DOWNLOAD_CHUNK_SIZE
        for chunk_idx in tqdm(range(num_chunks), desc="Fetching centroided spectra"):
            chunk = to_fetch[
                chunk_idx * DOWNLOAD_CHUNK_SIZE : (chunk_idx + 1) * DOWNLOAD_CHUNK_SIZE
            ]
            centroided_map = msdk.get_sample_centroids_per_scan(
                mascope_url=data_browser.mascope_url,
                access_token=data_browser.access_token,
                sample_item_ids=chunk,
            )
            if not centroided_map:
                raise ValueError(
                    f"No centroided data found for sample_item_ids: {chunk}. "
                    "Check if Mascope server is running and has centroided data."
                )
            for sample_item_id, centroids in centroided_map.items():
                # Build CentroidedSpectrum list per scan
                spec_list = [
                    CentroidedSpectrum(
                        mz=mzs,
                        intensity=intensities,
                        resolution=resolutions,
                        signal_to_noise=snr,
                        metadata={"sample_item_id": sample_item_id},
                    )
                    for mzs, intensities, resolutions, snr in zip(
                        centroids["masses"],
                        centroids["intensities"],
                        centroids["resolutions"],
                        centroids["signal_to_noise"],
                    )
                ]
                timestamps = np.asarray(centroids["timestamp"], dtype=float)
                # Save/refresh cache
                _save_cache(sample_item_id, spec_list, timestamps)
                per_sample_data[sample_item_id] = (spec_list, timestamps)
    # Gather outputs in the exact input order with correct time offsets
    spectra = []
    batch_scan_timestamps = []
    for row_idx, sample_item_id in enumerate(sample_item_ids):
        spec_list, timestamps = per_sample_data[sample_item_id]
        spectra.extend(spec_list)
        batch_scan_timestamps.extend(timestamps + time_since_first_sample_s[row_idx])

    return Spectra(spectra, np.asarray(batch_scan_timestamps, dtype=float))


def average_sample_item_spectra(
    sample_item_ids: list[str],
    data_browser: "MascopeDataBrowser",
    calibration_factors: list | None = None,
    method="mean",
) -> dict[str, np.ndarray]:
    """Calculate the averaged spectrum from the spectra of multiple sample items.
    This function retrieves the spectra for each sample item ID, calibrates their m/z values if
    calibration factors are provided, interpolates them onto a common m/z grid,
    and then averages the intensities at each m/z value.

    :param sample_item_ids: List of sample item IDs for which to average spectra.
    :type sample_item_ids: list[str]
    :param data_browser: MascopeDataBrowser instance for accessing Mascope data.
    :type data_browser: MascopeDataBrowser
    :param calibration_factors: List of m/z calibration factors for each sample item ID, defaults to None
    :param method: Averaging method, defaults to "mean"
    :type method: str, optional
    :raises ValueError: If the method is not 'mean' or 'median'.
    :return: A dictionary with 'mz' and 'intensity' keys, where 'mz' is the common m/z grid and 'intensity' is the averaged intensity at each m/z.
    :rtype: dict
    """
    if calibration_factors is not None:
        calibration_factors = np.asarray(calibration_factors, dtype=float)
    else:
        calibration_factors = np.ones(len(sample_item_ids), dtype=float)

    averaged_specs = []
    num_chunks = (len(sample_item_ids) + DOWNLOAD_CHUNK_SIZE - 1) // DOWNLOAD_CHUNK_SIZE

    for chunk_idx in tqdm(range(num_chunks), desc="Processing sample_item_ids"):
        chunk = sample_item_ids[
            chunk_idx * DOWNLOAD_CHUNK_SIZE : (chunk_idx + 1) * DOWNLOAD_CHUNK_SIZE
        ]
        chunk_averaged_specs = msdk.get_samples_spectra(
            mascope_url=data_browser.mascope_url,
            access_token=data_browser.access_token,
            sample_item_ids=chunk,
        )
        if not chunk_averaged_specs:
            raise ValueError(
                f"No spectra found for sample_item_ids: {chunk}. "
                "Check if Mascope server is running and has spectrum data."
            )
        averaged_specs.extend(chunk_averaged_specs)

    # Apply calibration to m/z values
    for i, cal in enumerate(calibration_factors):
        mz_arr = np.asarray(averaged_specs[i]["mz"], dtype=float)
        averaged_specs[i]["mz"] = mz_arr * cal

    # 1. Get all unique m/z values across all spectra
    union_mz = np.unique(np.concatenate([spec["mz"] for spec in averaged_specs]))
    union_mz = np.sort(union_mz)

    # 2. Interpolate each spectrum's intensity onto the union m/z grid
    interpolated_spectra = []
    for spec in averaged_specs:
        interp = np.interp(union_mz, spec["mz"], spec["intensity"], left=0, right=0)
        interpolated_spectra.append(interp)
    interpolated_spectra = np.vstack(interpolated_spectra)

    # 3. Average intensities at each m/z
    if method == "mean":
        avg_intensity = np.mean(interpolated_spectra, axis=0)
    elif method == "median":
        avg_intensity = np.median(interpolated_spectra, axis=0)
    else:
        raise ValueError("method must be 'mean' or 'median'")

    return {"mz": union_mz, "intensity": avg_intensity}


def filter_centroids(
    spectra: Spectra, min_intensity: float = 0, snr_threshold: float = 3
) -> Spectra:
    """
    Filters out noise centroids from the spectra based on minimum intensity and SNR threshold.

    :param spectra: Spectra object containing centroided spectra.
    :type spectra: Spectra
    :param min_intensity: Minimum intensity threshold for filtering, defaults to 0.
    :type min_intensity: float, optional
    :param snr_threshold: Minimum signal-to-noise ratio threshold for filtering, defaults to 3.
    :type snr_threshold: float, optional
    :return: Filtered Spectra object with noise centroids removed.
    :rtype: Spectra
    """
    filtered_spectra = []
    for spec in spectra:
        mask = (spec.intensity >= min_intensity) & (
            spec.signal_to_noise >= snr_threshold
        )
        filtered_spectra.append(
            CentroidedSpectrum(
                mz=spec.mz[mask],
                intensity=spec.intensity[mask],
                resolution=spec.resolution[mask],
                signal_to_noise=spec.signal_to_noise[mask],
                metadata=spec.metadata,
            )
        )
    return Spectra(filtered_spectra, spectra.timestamps)


def flag_satellite_peaks(
    peaks: pd.DataFrame,
    base_peak_percentile: float = 99.9,
    top_n_bases: int | None = None,
    window_ppm: float = 10.0,
    ratio_max: float = 0.1,
    ratio_min: float = 0.0001,
    symmetry_tolerance_ppm: float = 5.0,
    isotope_tolerance_ppm: float = 5.0,
    charge_range: tuple[int, int] = (1, 3),
) -> pd.DataFrame:
    """Flag Thermo/FTMS satellite peaks around very intense base peaks.
    Adds a boolean column 'is_satellite_peak' to the returned DataFrame.

    Heuristics:
    - Satellites are much weaker than the base peak and lie within a narrow ppm window.
    - They tend to appear symmetrically around the base.
    - Isotopes (+1.003355/z) are excluded.

    :param peaks: DataFrame containing peaks with 'mz' and 'intensity' columns.
    :type peaks: pd.DataFrame
    :param base_peak_percentile: Percentile for selecting base peaks, defaults to 99.9.
    :type base_peak_percentile: float, optional
    :param top_n_bases: If specified, overrides the percentile and selects the top N bases.
    :type top_n_bases: int | None, optional
    :param window_ppm: Search window around base peaks in ppm, defaults to 10.0.
    :type window_ppm: float, optional
    :param ratio_max: Maximum intensity ratio for satellite peaks relative to base peaks, defaults to 0.1.
    :type ratio_max: float, optional
    :param ratio_min: Minimum intensity ratio for satellite peaks relative to base peaks, defaults to 0.0001.
    :type ratio_min: float, optional
    :param symmetry_tolerance_ppm: Tolerance for symmetric pairing around the base peak in ppm, defaults to 5.0.
    :type symmetry_tolerance_ppm: float, optional
    :param isotope_tolerance_ppm: Tolerance for excluding +1 isotopes in ppm, defaults to 5.0.
    :type isotope_tolerance_ppm: float, optional
    :param charge_range: Range of charge states to consider for isotopes, defaults to (1, 3).
    :type charge_range: tuple[int, int], optional
    :return: DataFrame with an additional boolean column 'is_satellite_peak' indicating satellite peaks.
    :rtype: pd.DataFrame
    """
    flagged_peaks = peaks.copy()
    if flagged_peaks.empty:
        flagged_peaks["is_satellite_peak"] = False
        return flagged_peaks

    mz = flagged_peaks["mz"].to_numpy()
    intensity = flagged_peaks["intensity"].to_numpy()

    order = np.argsort(mz)
    mz_sorted = mz[order]
    intensity_sorted = intensity[order]
    num_of_peaks = mz_sorted.size

    # Choose base peaks
    base_peak_threshold = np.percentile(intensity_sorted, base_peak_percentile)
    base_mask = intensity_sorted >= base_peak_threshold
    if top_n_bases is not None and top_n_bases < base_mask.sum():
        idx_bases = np.flatnonzero(base_mask)
        top_local = idx_bases[
            np.argsort(intensity_sorted[idx_bases])[::-1][:top_n_bases]
        ]
        base_mask[:] = False
        base_mask[top_local] = True
    base_idx = np.flatnonzero(base_mask)

    is_satellite_sorted = np.zeros(num_of_peaks, dtype=bool)

    for base_index in base_idx:
        base_mass = mz_sorted[base_index]
        base_intensity = intensity_sorted[base_index]
        if base_intensity <= 0:
            continue

        window_da = ppm_to_da(base_mass, window_ppm)
        lower_window_index = np.searchsorted(
            mz_sorted, base_mass - window_da, side="left"
        )
        upper_window_index = np.searchsorted(
            mz_sorted, base_mass + window_da, side="right"
        )

        # Relative intensity filter
        candidate_indices = [
            i for i in range(lower_window_index, upper_window_index) if i != base_index
        ]
        candidate_indices = [
            i
            for i in candidate_indices
            if ratio_min <= (intensity_sorted[i] / base_intensity) <= ratio_max
        ]
        if not candidate_indices:
            continue

        # Exclude +1 isotopes on high-mass side
        kept = []
        for i in candidate_indices:
            dmz = mz_sorted[i] - base_mass
            if dmz <= 0:
                kept.append(i)
                continue
            is_isotope = False
            for z in range(charge_range[0], charge_range[1] + 1):
                isotope_da = 1.0033548378 / z
                tolerance_da = max(
                    ppm_to_da(base_mass, isotope_tolerance_ppm),
                    ppm_to_da(base_mass + dmz, isotope_tolerance_ppm),
                )
                if abs(dmz - isotope_da) <= tolerance_da:
                    is_isotope = True
                    break
            if not is_isotope:
                kept.append(i)
        candidate_indices = kept
        if not candidate_indices:
            continue

        # Symmetry pairing around the base
        tolerance_symmetry_da = ppm_to_da(base_mass, symmetry_tolerance_ppm)
        candidates_set = set(candidate_indices)
        used = set()
        for i in list(candidate_indices):
            if i in used:
                continue
            dmz = mz_sorted[i] - base_mass
            target_mass = base_mass - dmz
            left_symmetry_index = np.searchsorted(
                mz_sorted, target_mass - tolerance_symmetry_da, side="left"
            )
            right_symmetry_index = np.searchsorted(
                mz_sorted, target_mass + tolerance_symmetry_da, side="right"
            )

            mirror = None
            for k in range(left_symmetry_index, right_symmetry_index):
                if k == base_index or k == i:
                    continue
                if k in candidates_set:
                    mirror = k
                    break

            if mirror is not None:
                intensity_ratio_candidate = intensity_sorted[i] / base_intensity
                mirror_intensity_ratio = intensity_sorted[mirror] / base_intensity
                if (
                    min(intensity_ratio_candidate, mirror_intensity_ratio)
                    / max(intensity_ratio_candidate, mirror_intensity_ratio)
                    >= 0.5
                ):  # similar magnitude
                    is_satellite_sorted[i] = True
                    is_satellite_sorted[mirror] = True
                    used.add(i)
                    used.add(mirror)
            else:
                # Single-sided artifact near base, very low ratio
                if abs(dmz) <= ppm_to_da(base_mass, min(5.0, window_ppm)) and (
                    intensity_sorted[i] / base_intensity
                ) <= min(ratio_max, 0.03):
                    is_satellite_sorted[i] = True
                    used.add(i)

    # Back to original order
    is_satellite = np.zeros(num_of_peaks, dtype=bool)
    is_satellite[order] = is_satellite_sorted
    flagged_peaks["is_satellite_peak"] = is_satellite
    return flagged_peaks
