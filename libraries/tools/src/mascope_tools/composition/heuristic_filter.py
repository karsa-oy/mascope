"""Based on 7 Golden Rules by https://bmcbioinformatics.biomedcentral.com/articles/10.1186/1471-2105-8-105"""

from typing import Any
import re
import warnings
from functools import lru_cache
import numpy as np
from scipy.spatial.distance import cosine
import polars as pl
from IsoSpecPy import IsoThreshold
from composition.models import HeuristicRuleWarning
from composition.constants import (
    DEFAULT_ELEMENTAL_RATIO_RANGE,
    ISOTOPE_ABUNDANCE_THRESHOLD,
    ELECTRON_MASS,
    ISOTOPE_MATCHING_MZ_TOLERANCE_PPM,
    ISOTOPIC_PATTERN_THRESHOLD,
)

# Limit isotopic matching to the most plausible candidates
ISOTOPE_CANDIDATE_LIMIT = 64

# Lightweight, cached formula parser (much faster than pyteomics.Composition)
_FORMULA_RE = re.compile(r"([A-Z][a-z]?(?:\[\d+\])?)(\d+)")


@lru_cache(maxsize=16384)
def _parse_counts(formula: str) -> dict[str, int]:
    return {el: int(n) for el, n in _FORMULA_RE.findall(formula)}


@lru_cache(maxsize=20000)
def _cached_isotope_pattern(ion_formula: str, threshold: float):
    peaks = IsoThreshold(formula=ion_formula, threshold=threshold)
    # Return tuples to keep cacheable
    return (tuple(peaks.masses), tuple(peaks.probs))


def rule_element_ratio(candidates: pl.DataFrame, **kwargs) -> pl.Series:

    params = kwargs.get("params", {})
    if "elemental_ratio_range" in params:
        element_ratio_range = params["elemental_ratio_range"]
    else:
        element_ratio_range = DEFAULT_ELEMENTAL_RATIO_RANGE

    """Elemental ratio constraints (e.g., H/C, N/C, O/C)."""
    formulas = candidates.get_column("formula").to_list()
    # Fast cached parsing
    counts_list = [_parse_counts(f) for f in formulas]
    counts = pl.DataFrame(counts_list).fill_null(0)

    # Start with all True
    element_ratio_mask = pl.Series([True] * counts.height)

    # Only apply ratio rules where carbon is present
    if "C" not in counts.columns:
        warnings.warn(
            "No carbon atoms found in formulas; element ratios were skipped.",
            HeuristicRuleWarning,
        )
        return element_ratio_mask

    has_carbon = counts["C"] > 0

    for ratio, (min_val, max_val) in element_ratio_range.items():
        num, denom = ratio.split("/")
        if num not in counts.columns or denom not in counts.columns:
            continue  # Skip if ratio elements are not present
        numerator = counts[num]
        denominator = counts[denom]
        # Avoid division by zero
        ratio_val = numerator / denominator
        ratio_val = ratio_val.fill_nan(float("nan"))
        # Only update mask for formulas with carbon
        mask = (ratio_val >= min_val) & (ratio_val <= max_val)
        element_ratio_mask = element_ratio_mask & (~has_carbon | mask)

    if (~has_carbon).sum() > 0:
        warnings.warn(
            "Some formulas have zero carbon atoms; element ratios were skipped for these.",
            HeuristicRuleWarning,
        )

    return element_ratio_mask


def rule_valence(candidates: pl.DataFrame, **kwargs) -> pl.Series:
    """Valence rules (even/odd electron)."""
    # TODO: requires charge and electron count info
    return pl.Series([True] * candidates.height)  # Placeholder, always returns True


def rule_senior(candidates: pl.DataFrame, **kwargs) -> pl.Series:
    """Senior's rules (structural feasibility)."""
    # TODO: requires graph theory/structure generation
    return pl.Series([True] * candidates.height)  # Placeholder, always returns True


def rule_known_chemical_space(candidates: pl.DataFrame, **kwargs) -> pl.Series:
    """Known chemical space (database matching)."""
    # TODO: requires access to some chemical database
    return pl.Series([True] * candidates.height)  # Placeholder, always returns True


# From lightweight to heavyweight, these rules are applied in order.
HEURISTIC_RULES = [
    rule_element_ratio,
    rule_valence,
    rule_senior,
    rule_known_chemical_space,
]


def apply_heuristic_rules(
    candidates: list[dict[str, Any]],
    params: dict[str, Any] = {},
) -> list[dict[str, Any]]:
    """
    Filter candidate formulas using the heuristic rules.
    Returns only those that pass all rules.

    :param candidates: List of candidate formula dicts (or Result objects).
    :return: Filtered list of candidates.
    """
    candidates = pl.DataFrame(candidates)
    if candidates.is_empty():
        warnings.warn(
            "No candidates provided for heuristic filtering.",
            HeuristicRuleWarning,
        )
        return []

    if "Ionization peak" in candidates.get_column("formula").to_list():
        # Skip all rules for ionization peaks
        return candidates.filter(pl.col("formula") == "Ionization peak").to_dicts()

    for i, rule in enumerate(HEURISTIC_RULES):
        if candidates.is_empty():
            warnings.warn(
                f"No candidates passed the rule: {HEURISTIC_RULES[i-1].__name__}",
                HeuristicRuleWarning,
            )
            break
        rule_mask = rule(candidates, params)
        candidates = candidates.filter(rule_mask)

    return candidates.to_dicts()


def match_isotopic_pattern(
    candidates: list[dict[str, Any]], peaks: pl.DataFrame
) -> tuple[list[dict[str, Any]], np.ndarray]:
    """Matches isotopic patterns against candidates.

    :param candidates: DataFrame of candidate formulas.
    :type candidates: pl.DataFrame
    :param peaks: DataFrame of peaks with 'mz' and 'intensity' columns.
    :type peaks: pl.DataFrame
    :return: Tuple of filtered candidates and their corresponding isotope masses.
    :rtype: tuple[list[dict[str, Any]], np.ndarray]
    """
    if peaks is None or peaks.height == 0:
        # Return candidates untouched with zero scores, and no isotope masses
        if isinstance(candidates, list):
            if len(candidates) == 0:
                return [], np.array([])
            for c in candidates:
                c["isotopic_pattern_score"] = 0.0
            return candidates, np.array([])
        else:
            df = pl.DataFrame(candidates).with_columns(
                pl.lit(0.0, dtype=pl.Float64).alias("isotopic_pattern_score")
            )
            return df.to_dicts(), np.array([])

    peaks = peaks.sort("mz")
    mzs = peaks["mz"].to_numpy()
    intensities = peaks["intensity"].to_numpy()

    candidates = pl.DataFrame(candidates)
    if candidates.is_empty():
        candidates = candidates.with_columns(
            pl.lit(0.0, dtype=pl.Float64).alias("isotopic_pattern_score")
        )
        return candidates.to_dicts(), np.array([])

    # If ionization peak: skip isotopic matching and return score 1.0
    if "Ionization peak" in candidates.get_column("formula").to_list():
        candidates = candidates.with_columns(
            pl.lit(1.0, dtype=pl.Float64).alias("isotopic_pattern_score")
        )
        return candidates.to_dicts(), np.array([])

    # Keep only the most promising candidates for heavy work
    if "error_ppm" in candidates.columns:
        candidates = candidates.sort("error_ppm").head(ISOTOPE_CANDIDATE_LIMIT)

    ion_series = candidates.get_column("ion")
    ion_formulas = []
    ion_charges = []
    for i in ion_series:
        if i and isinstance(i, str) and len(i) >= 2 and i[-1] in "+-":
            ion_formulas.append(i[:-1])
            ion_charges.append(1 if i[-1] == "+" else -1)
        else:
            ion_formulas.append(i or "")
            ion_charges.append(1)  # default +1 if missing

    scores = np.zeros(len(candidates), dtype=float)
    best_observed_masses = np.array([])

    for ind, (ion_formula, ion_charge) in enumerate(zip(ion_formulas, ion_charges)):
        if not ion_formula:
            continue
        try:
            masses_t, probs_t = _cached_isotope_pattern(
                ion_formula, ISOTOPE_ABUNDANCE_THRESHOLD
            )
            if not masses_t:
                continue
            predicted_masses_neutral = np.fromiter(masses_t, dtype=float)
            predicted_intensities = np.fromiter(probs_t, dtype=float)
        except Exception:
            continue

        predicted_mzs = (predicted_masses_neutral - ELECTRON_MASS * ion_charge) / abs(
            ion_charge
        )

        observed_masses = np.zeros_like(predicted_mzs)
        observed_intensities = np.zeros_like(predicted_intensities)

        for i, p_mz in enumerate(predicted_mzs):
            mz_delta = p_mz * ISOTOPE_MATCHING_MZ_TOLERANCE_PPM * 1e-6
            mz_min, mz_max = p_mz - mz_delta, p_mz + mz_delta

            start_idx = np.searchsorted(mzs, mz_min, side="left")
            end_idx = np.searchsorted(mzs, mz_max, side="right")

            if start_idx < end_idx:
                # Take the max intensity in the window
                window = intensities[start_idx:end_idx]
                if window.size:
                    max_index = int(np.argmax(window))
                    observed_intensities[i] = window[max_index]
                    observed_masses[i] = mzs[start_idx + max_index]

        # Require monoisotopic detection
        if observed_intensities[0] > 0:
            observed_intensities /= observed_intensities[0]
            if predicted_intensities[0] > 0:
                predicted_intensities /= predicted_intensities[0]

            cosine_dist = cosine(predicted_intensities, observed_intensities)
            score = 1 - cosine_dist if not np.isnan(cosine_dist) else 0.0
            scores[ind] = score
            # Keep the observed masses from the best scoring candidate
            if score >= ISOTOPIC_PATTERN_THRESHOLD and (
                best_observed_masses.size == 0 or score > scores.max(initial=0.0)
            ):
                best_observed_masses = observed_masses

    candidates = candidates.with_columns(
        pl.Series(values=scores, name="isotopic_pattern_score")
    ).sort("isotopic_pattern_score", descending=True)

    return candidates.to_dicts(), best_observed_masses
