"""
Based on 7 Golden Rules by https://bmcbioinformatics.biomedcentral.com/articles/10.1186/1471-2105-8-105
"""

from typing import Any
import numpy as np
from scipy.spatial.distance import cosine
import polars as pl
from IsoSpecPy import IsoThreshold, ParseFormula, PeriodicTbl
from mascope_tools.composition.constants import (
    DEFAULT_ELEMENTAL_RATIO_RANGE,
    ISOTOPE_ABUNDANCE_THRESHOLD,
    ELECTRON_MASS,
    ISOTOPE_MATCHING_MZ_TOLERANCE_PPM,
    ISOTOPE_MATCHING_INTENSITY_TOLERANCE,
)

# Limit isotopic matching to the most plausible candidates
ISOTOPE_CANDIDATE_LIMIT = 64


def rule_element_ratio(
    candidates: pl.DataFrame, **kwargs
) -> tuple[pl.Series, list[str]]:
    log_messages = []
    params = kwargs.get("params", {})
    carbon_element_ratio_range = params.get(
        "carbon_element_ratio_range", DEFAULT_ELEMENTAL_RATIO_RANGE
    )
    non_carbon_element_ratio_range = params.get("non_carbon_element_ratio_range", {})

    formulas = candidates.get_column("formula").to_list()
    counts_list = [ParseFormula(f) for f in formulas]
    counts = pl.DataFrame(counts_list)
    if "C" in counts.columns:
        has_carbon = counts.get_column("C") > 0
    else:
        has_carbon = pl.Series([False] * counts.height)

    def apply_ratio_rules(ratio_range, mask_condition):
        mask = pl.Series([True] * counts.height)
        for ratio, (min_val, max_val) in ratio_range.items():
            num, denom = ratio.split("/")
            if num not in counts.columns or denom not in counts.columns:
                continue
            numerator = counts[num]
            denominator = counts[denom]
            ratio_val = numerator / denominator
            ratio_val = ratio_val.fill_nan(float("nan"))
            rule_mask = (ratio_val >= min_val) & (ratio_val <= max_val)
            mask = mask & (mask_condition | rule_mask)
        return mask

    # Apply carbon ratios where C > 0
    mask_carbon = apply_ratio_rules(carbon_element_ratio_range, ~has_carbon)
    # Apply non-carbon ratios where C == 0
    mask_non_carbon = apply_ratio_rules(non_carbon_element_ratio_range, has_carbon)
    # Combine both masks
    element_ratio_mask = mask_carbon & mask_non_carbon

    return element_ratio_mask, log_messages


def rule_valence(candidates: pl.DataFrame, **kwargs) -> tuple[pl.Series, list[str]]:
    """Valence rules (even/odd electron)."""
    # TODO: requires charge and electron count info
    mask = pl.Series([True] * candidates.height)
    log_messages = []
    return mask, log_messages  # Placeholder, always returns True


def rule_senior(candidates: pl.DataFrame, **kwargs) -> tuple[pl.Series, list[str]]:
    """Senior's rules (structural feasibility)."""
    # TODO: requires graph theory/structure generation
    mask = pl.Series([True] * candidates.height)
    log_messages = []
    return mask, log_messages  # Placeholder, always returns True


def rule_known_chemical_space(
    candidates: pl.DataFrame, **kwargs
) -> tuple[pl.Series, list[str]]:
    """Known chemical space (database matching)."""
    # TODO: requires access to some chemical database
    mask = pl.Series([True] * candidates.height)
    log_messages = []
    return mask, log_messages  # Placeholder, always returns True


# From lightweight to heavyweight, these rules are applied in order.
HEURISTIC_RULES = [
    rule_element_ratio,
    rule_valence,
    rule_senior,
    rule_known_chemical_space,
]


def apply_heuristic_rules(
    candidates: list[dict[str, Any]],
    params: dict[str, Any] = None,
) -> list[dict[str, Any]]:
    """
    Filter candidate formulas using the heuristic rules.
    Returns only those that pass all rules.

    :param candidates: List of candidate formula dicts (or Result objects).
    :return: Filtered list of candidates.
    """
    if params is None:
        params = {}
    log_messages = []
    candidates = pl.DataFrame(candidates)
    if candidates.is_empty():
        log_messages.append("No candidates provided for heuristic filtering.")
        return [], log_messages

    if "Ionization peak" in candidates.get_column("formula").to_list():
        # Skip all rules for ionization peaks
        return (
            candidates.filter(pl.col("formula") == "Ionization peak").to_dicts(),
            log_messages,
        )

    for i, rule in enumerate(HEURISTIC_RULES):
        if candidates.is_empty():
            log_messages.append(
                f"No candidates from passed the rule: {HEURISTIC_RULES[i-1].__name__}"
            )
            break
        rule_mask, rule_log_messages = rule(candidates, params=params)
        log_messages.extend(rule_log_messages)
        candidates = candidates.filter(rule_mask)

    return candidates.to_dicts(), log_messages


def match_isotopic_pattern(
    candidates: list[dict[str, Any]], peaks: pl.DataFrame
) -> tuple[list[dict[str, Any]], list[dict[str, np.ndarray | list[str]]]]:
    """Matches isotopic patterns against candidates.

    :param candidates: List of candidate formula dicts.
    :type candidates: list[dict[str, Any]]
    :param peaks: Sorted dataframe of peaks with 'mz' and 'intensity' columns.
    :type peaks: pl.DataFrame
    :return: Tuple of filtered candidates, and a list of isotope data dicts (per candidate).
    :rtype: tuple[list[dict[str, Any]], list[dict[str, np.ndarray | list[str]]]]
    """
    mzs = peaks["mz"].to_numpy()
    intensities = peaks["intensity"].to_numpy()

    candidates_df = pl.DataFrame(candidates)
    if candidates_df.is_empty():
        candidates_df = candidates_df.with_columns(
            pl.lit(0.0, dtype=pl.Float64).alias("isotopic_pattern_score")
        )
        return candidates_df.to_dicts(), []

    # Keep only the most promising candidates for heavy work
    candidates_df = candidates_df.sort("composition_error_ppm").head(
        ISOTOPE_CANDIDATE_LIMIT
    )

    # If ionization peak: skip isotopic matching and return score 1.0
    if "Ionization peak" in candidates_df.get_column("formula").to_list():
        candidates_df = candidates_df.with_columns(
            pl.lit(1.0, dtype=pl.Float64).alias("isotopic_pattern_score")
        )
        return candidates_df.to_dicts(), []

    ion_formulas, ion_charges = _extract_formulae_and_charges(
        candidates_df.get_column("ion")
    )

    scores = np.zeros(candidates_df.height, dtype=float)
    all_isotope_data = []

    for ind, (ion_formula, ion_charge) in enumerate(zip(ion_formulas, ion_charges)):
        predicted_mzs, predicted_intensities, isotope_labels = predict_isotopes(
            ion_formula, ion_charge
        )
        is_isotope_predicted = len(predicted_mzs) > 0
        if not is_isotope_predicted:
            all_isotope_data.append(
                {
                    "masses": [],
                    "mass_errors_ppm": [],
                    "intensity_errors": [],
                    "labels": [],
                    "predicted_masses": [],
                    "predicted_intensities": [],
                }
            )
            continue

        observed_masses = np.zeros_like(predicted_mzs)
        observed_intensities = observed_masses.copy()
        observed_mass_errors_ppm = observed_masses.copy()
        observed_intensity_error = observed_masses.copy()

        # Normalize predicted intensities relative to monoisotopic (base) peak
        predicted_rel = predicted_intensities / predicted_intensities[0]

        base_peak_intensity = None
        for i, p_mz in enumerate(predicted_mzs):
            mz_delta = p_mz * ISOTOPE_MATCHING_MZ_TOLERANCE_PPM * 1e-6
            mz_min, mz_max = p_mz - mz_delta, p_mz + mz_delta

            start_idx = np.searchsorted(mzs, mz_min, side="left")
            end_idx = np.searchsorted(mzs, mz_max, side="right")
            no_peaks_in_window = start_idx >= end_idx

            if no_peaks_in_window:
                continue

            window_mzs = mzs[start_idx:end_idx]
            window_intensities = intensities[start_idx:end_idx]
            if not window_mzs.size:
                continue

            matched_index = np.argmin(np.abs(window_mzs - p_mz))
            matched_mz = window_mzs[matched_index]
            matched_intensity = window_intensities[matched_index]
            is_base_peak = i == 0

            if is_base_peak:
                base_peak_intensity = matched_intensity
                observed_intensities[0] = matched_intensity
                observed_masses[0] = matched_mz
                observed_mass_errors_ppm[0] = abs(matched_mz - p_mz) / p_mz * 1e6
                observed_intensity_error[0] = 0.0
                continue  # move to next isotope

            # Require monoisotopic established before evaluating higher isotopes
            if base_peak_intensity is None or base_peak_intensity == 0:
                continue

            predicted_rel_intensity = predicted_rel[i]
            observed_rel_intensity = matched_intensity / base_peak_intensity
            intensity_error = (
                abs(predicted_rel_intensity - observed_rel_intensity)
                / predicted_rel_intensity
            )

            if intensity_error <= ISOTOPE_MATCHING_INTENSITY_TOLERANCE:
                observed_intensities[i] = matched_intensity
                observed_masses[i] = matched_mz
                observed_mass_errors_ppm[i] = abs(matched_mz - p_mz) / p_mz * 1e6
                observed_intensity_error[i] = intensity_error

        scores[ind] = score_pattern(
            observed_masses,
            observed_mass_errors_ppm,
            observed_intensities,
            observed_intensity_error,
            predicted_rel,
        )

        matched_isotopes = {
            "masses": observed_masses,
            "mass_errors_ppm": observed_mass_errors_ppm,
            "intensity_errors": observed_intensity_error,
            "labels": isotope_labels,
            "predicted_masses": predicted_mzs,
            "predicted_intensities": predicted_rel,
        }

        all_isotope_data.append(matched_isotopes)

    candidates_df = candidates_df.with_columns(
        pl.Series(values=scores, name="isotopic_pattern_score")
    ).sort("isotopic_pattern_score", descending=True)

    score_sorted_indices = np.argsort(scores)[::-1]
    all_isotope_data = [all_isotope_data[i] for i in score_sorted_indices]

    return candidates_df.to_dicts(), all_isotope_data


def predict_isotopes(
    ion_formula: str, ion_charge: int
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Predict isotopic pattern for a given ion formula and charge.

    :param ion_formula: Ion formula string.
    :type ion_formula: str
    :param ion_charge: Ion charge (e.g., +1, -1).
    :type ion_charge: int
    :return: Tuple of predicted m/z values, relative intensities, and isotope labels.
    :rtype: tuple[np.ndarray, np.ndarray, list[str]]
    """
    try:
        predicted_peaks = IsoThreshold(
            formula=ion_formula,
            threshold=ISOTOPE_ABUNDANCE_THRESHOLD,
            get_confs=True,
        )
        predicted_masses_neutral = np.fromiter(predicted_peaks.masses, dtype=float)
        predicted_intensities = np.fromiter(predicted_peaks.probs, dtype=float)

        composition = ParseFormula(ion_formula)
        elements = list(composition.keys())
        elemental_masses = [PeriodicTbl.symbol_to_masses[el] for el in elements]
        isotope_labels = [
            conf_to_label(conf, elements, elemental_masses)
            for conf in predicted_peaks.confs
        ]
        # Convert neutral masses to m/z
        predicted_mzs = (predicted_masses_neutral - ELECTRON_MASS * ion_charge) / abs(
            ion_charge
        )
    except Exception:
        predicted_mzs, predicted_intensities, isotope_labels = [], [], []

    return predicted_mzs, predicted_intensities, isotope_labels


def score_pattern(
    observed_masses: np.ndarray,
    observed_mass_errors_ppm: np.ndarray,
    observed_intensities: np.ndarray,
    observed_intensity_error: np.ndarray,
    predicted_rel: np.ndarray,
) -> float:
    """
    Scores the match between observed and predicted isotopic patterns.
    Returns a score between 0 and 1, where 1 is a perfect match.
    """
    # Require monoisotopic detection
    if observed_intensities[0] > 0:
        observed_rel_intensities = observed_intensities / observed_intensities[0]
        matched_peaks_count = np.sum(observed_masses > 0)

        # 1. Pattern scoring
        cosine_dist = cosine(predicted_rel, observed_rel_intensities)
        pattern_score = 1 - cosine_dist if not np.isnan(cosine_dist) else 0.0

        # 2. Intensity scoring
        total_intensity_error = np.sum(observed_intensity_error)
        avg_intensity_error = (
            total_intensity_error / matched_peaks_count
            if matched_peaks_count > 0
            else ISOTOPE_MATCHING_INTENSITY_TOLERANCE
        )
        intensity_score = max(
            0, 1 - (avg_intensity_error / ISOTOPE_MATCHING_INTENSITY_TOLERANCE)
        )

        # 3. Mass Accuracy Score
        total_mass_error_ppm = np.sum(observed_mass_errors_ppm)
        avg_mass_error = (
            total_mass_error_ppm / matched_peaks_count
            if matched_peaks_count > 0
            else ISOTOPE_MATCHING_MZ_TOLERANCE_PPM
        )
        mass_score = max(0, 1 - (avg_mass_error / ISOTOPE_MATCHING_MZ_TOLERANCE_PPM))

        # 4. Combined score.
        # pattern_score and intensity_score get lower weights because they are less reliable,
        # we may have only base peak detected.
        score = 0.2 * pattern_score + 0.2 * intensity_score + 0.6 * mass_score
    else:
        score = 0.0

    return score


def conf_to_label(conf, elements, isotope_masses):
    """Return isotope label string.

    :param conf: isotope counts for each element in the formula.
    :type conf: list[list[int]]
    :param elements: list of elements in the formula.
    :type elements: list[str]
    :param isotope_masses: list of isotope masses for each element.
    :type isotope_masses: list[list[float]]
    """
    label_parts = []
    for el, iso_counts, iso_masses in zip(elements, conf, isotope_masses):
        for idx, count in enumerate(iso_counts):
            if count == 0:
                continue

            # For the most abundant isotope (usually index 0), skip label unless it's the only one (M0)
            if idx == 0:
                continue

            mass_number = int(round(iso_masses[idx]))

            label_parts.append(f"{mass_number}{el}{count if count > 1 else ''}")

    if not label_parts:
        return "M0"
    return "+".join(label_parts)


def _extract_formulae_and_charges(ions: pl.Series) -> tuple[list[str], list[int]]:
    """Extracts formulae and charges from ion strings

    :param ions: Array of ion strings.
    :type ions: pl.Series
    :return: Tuple of lists containing ion formulas and their charges.
    :rtype: tuple[list[str], list[int]]
    """
    ions_arr = ions.to_numpy().astype(str)
    # Get last character for each ion string
    last_chars = np.array([s[-1] if len(s) >= 1 else "" for s in ions_arr])
    # Check if last char is + or -
    is_charged = np.isin(last_chars, ["+", "-"])
    # Remove last char if charged, else keep as is
    ion_formulas = [
        s[:-1] if charged else s for s, charged in zip(ions_arr, is_charged)
    ]
    # Assign charge: +1 for '+', -1 for '-', else 1
    ion_charges = [1 if c == "+" else -1 if c == "-" else 1 for c in last_chars]
    return ion_formulas, ion_charges
