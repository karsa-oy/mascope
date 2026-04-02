import numpy as np
import pandas as pd
import ruptures as rpt


def rank_matches_by_peak_presence(
    matches: pd.DataFrame, matched_peak_timeseries: pd.DataFrame
) -> pd.DataFrame:
    """Rank matches by the number of scans in which their corresponding peaks appear.

    :param matches: DataFrame of matches.
    :type matches: pd.DataFrame
    :param matched_peak_timeseries: DataFrame of matched peak timeseries.
    :type matched_peak_timeseries: pd.DataFrame
    :return: Ranked matches DataFrame with 'appearance' column added.
    :rtype: pd.DataFrame
    """
    appearance = (matched_peak_timeseries.values > 0).sum(axis=1)
    peak_appearance_df = pd.DataFrame(
        {"mz": matched_peak_timeseries.index, "appearance": appearance}
    )

    ranked = matches.merge(
        peak_appearance_df, on="mz", how="left", suffixes=("", "_diff")
    ).sort_values(by="appearance", ascending=False)
    return ranked


def assign_intensity_change_score(
    matches: pd.DataFrame,
    matched_peak_timeseries: pd.DataFrame,
    n_changepoints: int = 2,
    smoothing_window: int = 11,
) -> pd.DataFrame:
    """Calculates a intensity change score for each m/z timeseries.

    This score measures how well the timeseries is described by a
    step-function model (i.e., a series of flat, horizontal segments).
    A score near 1.0 means a perfect fit (thew timeseries contains peaks).
    A score near 0.0 means a poor fit (like a noisy flat line or a ramp).

    This uses the "Binseg" algorithm from the 'ruptures' library.

    :param matches: DataFrame of matches.
    :type matches: pd.DataFrame
    :param matched_peak_timeseries: DataFrame of matched peak timeseries.
    :type matched_peak_timeseries: pd.DataFrame
    :param n_changepoints: Number of changepoints to detect.
    :type n_changepoints: int, optional
    :param smoothing_window: Window size for rolling mean smoothing.
    :type smoothing_window: int, optional
    :return: matches with step change scores added.
    :rtype: pd.DataFrame
    """
    print("Assiging peak intensity change scores (may take minutes)...")
    results = []

    # Ensure window is odd
    if smoothing_window % 2 == 0:
        smoothing_window += 1

    for mz, series in matched_peak_timeseries.iterrows():

        # --- Handle missing points ---
        series_numeric = pd.to_numeric(series, errors="coerce")
        series_filled = series_numeric.interpolate(method="linear").bfill().ffill()

        # Handle edge cases
        if series_filled.isnull().all() or series_filled.nunique() == 1:
            results.append({"mz": mz, "intensity_change_score": 0})
            continue

        signal = series_filled.values
        n_points = len(signal)

        # Ensure we have enough points to fit the model
        if n_points < (n_changepoints + 1) * 2:
            results.append({"mz": mz, "intensity_change_score": 0})
            continue

        # --- Calculate total sum of squares ---
        # This is the "cost" of a 0-changepoint model (a single flat line)
        global_mean = np.mean(signal)
        sse_total = np.sum((signal - global_mean) ** 2)

        if sse_total == 0:
            # Already a perfect flat line
            results.append({"mz": mz, "intensity_change_score": 0})
            continue

        # --- Find change points ---
        # smooth data to help the detector find the location
        # of the change points, avoiding noise-driven false positives.
        smoothed_signal = (
            series_filled.rolling(window=smoothing_window, min_periods=1, center=True)
            .mean()
            .bfill()
            .ffill()
            .values
        )

        # Use binary segmentation to find n_changepoints
        algo = rpt.Binseg(model="l2").fit(smoothed_signal)
        try:
            bkps = algo.predict(n_bkps=n_changepoints)
        except rpt.exceptions.NotEnoughPoints:
            results.append({"mz": mz, "intensity_change_score": 0})
            continue

        # bkps gives the end index of each segment. Prepend 0.
        segment_indices = [0] + bkps

        # --- Calculate model sum of squares (SSE_model) ---
        # Calculate cost using the filled signal, but the
        # changepoints found from the smoothed signal.
        sse_model = 0
        for start, end in zip(segment_indices[:-1], segment_indices[1:]):
            segment = signal[start:end]
            if len(segment) > 0:
                segment_mean = np.mean(segment)
                sse_model += np.sum((segment - segment_mean) ** 2)

        # --- Calculate final score (R-squared-like) ---
        # 1.0 = perfect step model fit
        # 0.0 = step model is no better than a single flat line
        score = 1 - (sse_model / sse_total)

        results.append({"mz": mz, "intensity_change_score": score})

    if not results:
        return pd.DataFrame(columns=["mz", "intensity_change_score"])

    results_df = pd.DataFrame(results).set_index("mz")

    assigned = matches.merge(results_df, on="mz", how="left")

    return assigned
