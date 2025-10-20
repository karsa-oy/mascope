import os
import mascope_sdk as msdk
import numpy as np
import pandas as pd
from .calibration import CentroidedSpectrum, Spectra
from .caching import CacheManager


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
MAX_RETRIES = 5 # Number of retries for fetching data from server


def create_cache_folder():
    os.makedirs(CACHE_FOLDER, exist_ok=True)


def ppm_to_da(mz0: float, ppm: float) -> float:
    return mz0 * ppm * 1e-6


def collect_spectra(
    mascope_url: str,
    access_token: str,
    samples: pd.DataFrame,
    update_cached: bool = False,
) -> Spectra:
    """
    Collects centroided spectra and their corresponding timestamps from a set of samples.

    :param mascope_url: URL of the Mascope server.
    :type mascope_url: str
    :param access_token: User's Jupyter access token.
    :type access_token: str
    :param samples: DataFrame containing sample metadata, must include 'datetime', 'sample_file_id', and 'polarity' columns.
    :type samples: pd.DataFrame
    :param update_cached: If True, will update the cache with new spectra, defaults to False.
    :type update_cached: bool, optional
    :return: Spectra object containing the collected centroided spectra and their timestamps.
    :rtype: Spectra
    """
    create_cache_folder()
    cache = CacheManager(CACHE_FOLDER)
    samples = samples.copy()
    samples["datetime"] = pd.to_datetime(samples["datetime"])
    samples = samples.sort_values("datetime").reset_index(drop=True)

    time_since_first_sample_s = (
        (samples.datetime - samples.datetime[0]).dt.total_seconds().values
    )
    sample_item_ids = samples.sample_item_id.values.tolist()

    # Decide which IDs to fetch vs load based on cache state and update flag
    if update_cached:
        to_fetch = sample_item_ids
        to_load = []
    else:
        to_fetch = [sid for sid in sample_item_ids if not cache.exists(sid)]
        to_load = [sid for sid in sample_item_ids if cache.exists(sid)]

    # Collect all data (per sample_item_id) into a dict
    per_sample_data: dict[str, tuple[list[CentroidedSpectrum], np.ndarray]] = {}

    # Load from cache
    for sid in tqdm(to_load, desc="Loading centroided spectra from cache"):
        loaded = cache.load(sid)
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
            for attempt in range(1, MAX_RETRIES + 1):
                centroided_map = msdk.get_sample_centroids_per_scan(
                    mascope_url=mascope_url,
                    access_token=access_token,
                    sample_item_ids=chunk,
                )
                if centroided_map:
                    break
                if attempt == MAX_RETRIES:
                    raise ValueError(
                        f"No centroided data found for sample_item_ids: {chunk} after {MAX_RETRIES} attempts. "
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
                cache.save(sample_item_id, (spec_list, timestamps))
                per_sample_data[sample_item_id] = (spec_list, timestamps)
    # Gather outputs in the exact input order with correct time offsets
    spectra: list[CentroidedSpectrum] = []
    batch_scan_timestamps: list[float] = []
    for row_idx, sample_item_id in enumerate(sample_item_ids):
        spec_list, timestamps = per_sample_data[sample_item_id]
        spectra.extend(spec_list)
        batch_scan_timestamps.extend(timestamps + time_since_first_sample_s[row_idx])

    return Spectra(spectra, np.asarray(batch_scan_timestamps, dtype=float))


def average_sample_item_spectra(
    mascope_url: str,
    access_token: str,
    sample_item_ids: list[str],
    calibration_factors: list[float] | None = None,
    method: str = "mean",
    update_cached: bool = False,
) -> dict[str, np.ndarray]:
    """
    Calculate the averaged spectrum from the spectra of multiple sample items.

    :param mascope_url: URL of the Mascope server.
    :type mascope_url: str
    :param access_token: User's Jupyter access token
    :type access_token: str
    :param sample_item_ids: List of sample item IDs for which to average spectra.
    :type sample_item_ids: list[str]
    :param calibration_factors: List of m/z calibration factors for each sample item ID, defaults to None
    :param method: Averaging method, defaults to "mean"
    :type method: str, optional
    :param update_cached: If True, will update the cache with new averaged spectra, defaults to False.
    :type update_cached: bool, optional
    :raises ValueError: If the method is not 'mean' or 'median'.
    :return: A dictionary with 'mz' and 'intensity' keys, where 'mz' is the common m/z grid and 'intensity' is the averaged intensity at each m/z.
    :rtype: dict
    """
    create_cache_folder()
    cache = CacheManager(CACHE_FOLDER)

    if calibration_factors is not None:
        calibration_factors = np.asarray(calibration_factors, dtype=float)
    else:
        calibration_factors = np.ones(len(sample_item_ids), dtype=float)

    avg_cache_key = {
        "type": "averaged_spectrum",
        "sample_item_ids": tuple(sample_item_ids),
        "calibration_factors": tuple(calibration_factors.tolist()),
        "method": method,
    }

    if not update_cached:
        cached_result = cache.load(avg_cache_key)
        if cached_result is not None:
            return cached_result

    per_sample_avg_keys = [
        (
            "averaged_spectrum_per_sample",
            sample_item_id,
            float(calibration_factors[i]),
            method,
        )
        for i, sample_item_id in enumerate(sample_item_ids)
    ]

    averaged_specs: list[dict[str, np.ndarray] | None] = [None] * len(sample_item_ids)
    loaded_mask = np.zeros(len(sample_item_ids), dtype=bool)

    for i, key in enumerate(
        tqdm(
            per_sample_avg_keys, desc="Check if some of averaged spectra are cached..."
        )
    ):
        if not update_cached:
            cached = cache.load(key)
            if cached is not None:
                averaged_specs[i] = cached
                loaded_mask[i] = True

    to_fetch_indices = (
        np.where(~loaded_mask)[0]
        if not update_cached
        else np.arange(len(sample_item_ids))
    )
    if len(to_fetch_indices) > 0:
        for chunk_start in tqdm(
            range(0, len(to_fetch_indices), DOWNLOAD_CHUNK_SIZE),
            desc="Fetching missing averaged spectra from server",
        ):
            chunk_indices = to_fetch_indices[
                chunk_start : chunk_start + DOWNLOAD_CHUNK_SIZE
            ]
            chunk_sample_ids = [sample_item_ids[i] for i in chunk_indices]
            chunk_cal_factors = [float(calibration_factors[i]) for i in chunk_indices]
            chunk_keys = [per_sample_avg_keys[i] for i in chunk_indices]

            for attempt in range(1, MAX_RETRIES + 1):
                chunk_averaged_specs = msdk.get_samples_spectra(
                    mascope_url=mascope_url,
                    access_token=access_token,
                    sample_item_ids=chunk_sample_ids,
                )
                if chunk_averaged_specs and len(chunk_averaged_specs) == len(
                    chunk_sample_ids
                ):
                    break
                if attempt == MAX_RETRIES:
                    raise ValueError(
                        f"No spectra found for sample_item_ids: {chunk_sample_ids} after {MAX_RETRIES} attempts. "
                        "Check if Mascope server is running and has spectrum data."
                    )

            for spec, cal, key, arr_idx in zip(
                chunk_averaged_specs, chunk_cal_factors, chunk_keys, chunk_indices
            ):
                mz_arr = np.asarray(spec["mz"], dtype=float) * cal
                spec["mz"] = mz_arr
                cache.save(key, spec)
                averaged_specs[arr_idx] = spec

    if any(spec is None for spec in averaged_specs):
        missing = [i for i, spec in enumerate(averaged_specs) if spec is None]
        raise RuntimeError(
            f"Failed to load or fetch averaged spectra for indices: {missing}"
        )

    union_mz = np.unique(np.concatenate([spec["mz"] for spec in averaged_specs]))
    union_mz = np.sort(union_mz)

    n = len(averaged_specs)
    if method == "mean":
        sum_intensity = np.zeros_like(union_mz)
        for spec in averaged_specs:
            sum_intensity += np.interp(
                union_mz, spec["mz"], spec["intensity"], left=0, right=0
            )
        avg_intensity = sum_intensity / n
    elif method == "median":
        # For median, chunking is not possible; fallback to stacking for correctness
        interpolated_spectra = np.empty((n, union_mz.size), dtype=float)
        for i, spec in enumerate(averaged_specs):
            interpolated_spectra[i] = np.interp(
                union_mz, spec["mz"], spec["intensity"], left=0, right=0
            )
        avg_intensity = np.median(interpolated_spectra, axis=0)
    else:
        raise ValueError("method must be 'mean' or 'median'")

    result = {"mz": union_mz, "intensity": avg_intensity}
    cache.save(avg_cache_key, result)
    return result


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
