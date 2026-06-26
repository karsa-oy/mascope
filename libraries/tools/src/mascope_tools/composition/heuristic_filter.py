"""
Based on 7 Golden Rules by https://bmcbioinformatics.biomedcentral.com/articles/10.1186/1471-2105-8-105
"""

from typing import Any

import numpy as np
import polars as pl
from IsoSpecPy import IsoDistribution, IsoThreshold, PeriodicTbl
from pyteomics.mass import Composition
from scipy.spatial.distance import cosine

from mascope_tools.composition.config import (
    ELECTRON_MASS,
    ISOTOPE_ABUNDANCE_THRESHOLD,
    ISOTOPE_MATCHING_INTENSITY_TOLERANCE,
    ISOTOPE_MATCHING_MZ_TOLERANCE_PPM,
)
from mascope_tools.composition.custom_elements import CUSTOM_ELEMENTS
from mascope_tools.composition.models import HeuristicFilterConfig
from mascope_tools.composition.utils import (
    normalize_formula_with_isotopes,
    to_pyteomics,
)


# Limit isotopic matching to the most plausible candidates
ISOTOPE_CANDIDATE_LIMIT = 64

# --- Labelled-reagent custom elements ('^X' notation) ------------------------
# A labelled reagent atom is not 100% pure; e.g. 15N-nitrate is ~98% 15N / 2% 14N.
# We model it as a custom element '^X' whose isotope abundances are the labelled
# distribution, so predict_isotopes yields the heavy base AND the small light
# satellite. `purity` is the heaviest-isotope fraction (e.g. 0.98 for 15N).
# The element definitions come from the shared registry (custom_elements.py) --
# the single source of truth also used by the Mascope backend, so no molmass
# dependency and no duplicated isotope data.
LABELLED_REAGENT_PURITY = CUSTOM_ELEMENTS["^N"].default_purity
# symbol -> (regular_symbol, [(mass, mass_number), ... lightest first])
_CUSTOM_ELEMENT_DATA = {
    sym: (ce.base_element, list(ce.isotopes)) for sym, ce in CUSTOM_ELEMENTS.items()
}


def rule_element_ratio(
    candidates: pl.DataFrame, heuristics_config: HeuristicFilterConfig, **kwargs
) -> tuple[pl.Series, list[str]]:
    log_messages = []

    # Early return if no candidates
    if candidates.is_empty():
        return pl.Series([], dtype=pl.Boolean), log_messages

    formulas = candidates.get_column("formula").to_list()

    # Parse all formulas once and convert to a structured format
    counts_list = [
        Composition(formula=normalize_formula_with_isotopes(f)) for f in formulas
    ]

    # Get all unique elements across all formulas
    all_elements = set()
    for counts in counts_list:
        all_elements.update(counts.keys())
    all_elements = sorted(all_elements)

    # Create a matrix where rows are formulas and columns are elements
    n_formulas = len(counts_list)
    n_elements = len(all_elements)
    element_matrix = np.zeros((n_formulas, n_elements), dtype=np.int32)

    # Fill the matrix
    element_to_idx = {elem: idx for idx, elem in enumerate(all_elements)}
    for i, counts in enumerate(counts_list):
        for elem, count in counts.items():
            element_matrix[i, element_to_idx[elem]] = count

    # Determine which formulas have carbon
    carbon_idx = element_to_idx.get("C")
    has_carbon = carbon_idx is not None and element_matrix[:, carbon_idx] > 0

    # Initialize mask - all True initially
    final_mask = np.ones(n_formulas, dtype=bool)

    def apply_ratio_rules_vectorized(ratio_range, apply_to_mask):
        """Apply ratio rules using vectorized operations"""
        if not ratio_range or not np.any(apply_to_mask):
            return np.ones(n_formulas, dtype=bool)

        rule_mask = np.ones(n_formulas, dtype=bool)

        for ratio, (min_val, max_val) in ratio_range.items():
            num, denom = ratio.split("/")

            # Get indices for numerator and denominator elements
            num_idx = element_to_idx.get(num)
            denom_idx = element_to_idx.get(denom)

            if num_idx is None or denom_idx is None:
                continue

            # Get counts for numerator and denominator
            num_counts = element_matrix[:, num_idx]
            denom_counts = element_matrix[:, denom_idx]

            # Only apply rule where both elements exist and denominator > 0
            has_both_elements = (num_counts > 0) & (denom_counts > 0)
            applicable_mask = apply_to_mask & has_both_elements

            if not np.any(applicable_mask):
                continue

            # Calculate ratios only where applicable (avoid division by zero)
            ratios = np.full(n_formulas, np.inf)
            ratios[applicable_mask] = (
                num_counts[applicable_mask] / denom_counts[applicable_mask]
            )

            # Check if ratios are within bounds
            ratio_valid = (ratios >= min_val) & (ratios <= max_val)

            # Update rule mask: pass if not applicable OR ratio is valid
            rule_mask &= np.logical_not(applicable_mask) | ratio_valid

        return rule_mask

    # Apply carbon-specific ratios to formulas with carbon
    if np.any(has_carbon) and heuristics_config.carbon_element_ratio_range:
        carbon_mask = apply_ratio_rules_vectorized(
            heuristics_config.carbon_element_ratio_range, has_carbon
        )
        final_mask &= carbon_mask

    # Apply non-carbon ratios to formulas without carbon
    no_carbon = np.logical_not(has_carbon)
    if np.any(no_carbon) and heuristics_config.non_carbon_element_ratio_range:
        non_carbon_mask = apply_ratio_rules_vectorized(
            heuristics_config.non_carbon_element_ratio_range, no_carbon
        )
        final_mask &= non_carbon_mask

    return pl.Series(final_mask), log_messages


def rule_valence(candidates: pl.DataFrame, **kwargs) -> tuple[pl.Series, list[str]]:
    """Valence rules (even/odd electron)."""
    # TODO: requires charge and electron count info
    mask = pl.Series([True] * candidates.height)
    log_messages = []
    return mask, log_messages  # Placeholder, always returns True


# Standard valences for the RDBE / Senior structural checks (Golden Rule 2: Lewis &
# Senior). The classic organic convention (N,P trivalent; O,S divalent; halogens
# monovalent) makes RDBE a non-negative integer for any valid neutral, even-electron
# molecule. Any element OUTSIDE this table makes the check fail-open (the candidate is
# never rejected on valence grounds) so unusual chemistry is never wrongly cut.
_SENIOR_VALENCE = {
    "H": 1, "D": 1, "T": 1,
    "B": 3, "C": 4, "N": 3, "O": 2, "F": 1,
    "Si": 4, "P": 3, "S": 2, "Cl": 1,
    "Br": 1, "I": 1,
}


def rule_senior(candidates: pl.DataFrame, **kwargs) -> tuple[pl.Series, list[str]]:
    """Lewis & Senior structural feasibility (Seven Golden Rules, Rule 2).

    Rejects only a neutral formula that cannot correspond to ANY molecular graph:

    1. **RDBE ≥ 0** — the ring-and-double-bond equivalents
       ``RDBE = 1 + sum_i n_i (v_i - 2) / 2`` must be non-negative (negative ⇒
       over-saturated: more atoms than can be bonded, impossible for any structure).
    2. **Senior connectivity** — the sum of valences must be at least ``2*(N_atoms - 1)``
       so the atoms can form a single connected graph.

    Conservative / fail-open by design:
    - **Odd-electron (radical) formulas are NOT rejected.** A non-integer RDBE marks an
      open-shell species, which can be genuine (e.g. APCI/APPI radical ions); only the
      *impossible* (negative-RDBE) formulas are cut.
    - a formula containing any element outside ``_SENIOR_VALENCE`` (or that fails to parse)
      is never rejected here, so exotic compositions are never lost to this filter.

    Applies to NEUTRAL formulas only (as produced by ``find_compositions`` before
    ionization). See Kind & Fiehn 2007, BMC Bioinformatics 8:105 (Rule 2).
    """
    log_messages: list[str] = []
    if candidates.is_empty():
        return pl.Series([], dtype=pl.Boolean), log_messages

    mask: list[bool] = []
    for formula in candidates.get_column("formula").to_list():
        try:
            counts = Composition(formula=normalize_formula_with_isotopes(formula))
            elems = {el: n for el, n in counts.items() if n}
        except Exception:
            mask.append(True)  # unparseable here -> defer, never reject
            continue
        if not elems or any(el not in _SENIOR_VALENCE for el in elems):
            mask.append(True)  # fail-open on unknown elements
            continue
        n_atoms = sum(elems.values())
        valence_sum = sum(_SENIOR_VALENCE[el] * n for el, n in elems.items())
        # twice_rdbe = 2*RDBE. RDBE >= 0 rejects over-saturated formulas (impossible for
        # ANY structure). We deliberately do NOT require integer RDBE: an odd-electron
        # (radical) formula is left to pass, since radical species can be genuine.
        twice_rdbe = 2 + sum((_SENIOR_VALENCE[el] - 2) * n for el, n in elems.items())
        not_oversaturated = twice_rdbe >= 0
        connect_ok = n_atoms <= 1 or valence_sum >= 2 * (n_atoms - 1)
        mask.append(bool(not_oversaturated and connect_ok))
    return pl.Series(mask, dtype=pl.Boolean), log_messages


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
    heuristics_config: HeuristicFilterConfig | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """
    Filter candidate formulas using the heuristic rules.
    Returns only those that pass all rules.

    :param candidates: List of candidate formula dicts (or Result objects).
    :return: Filtered list of candidates.
    """
    if heuristics_config is None:
        heuristics_config = HeuristicFilterConfig()
    log_messages = []
    candidates_df = pl.DataFrame(candidates)
    if candidates_df.is_empty():
        log_messages.append("No candidates provided for heuristic filtering.")
        return [], log_messages

    if "()" in candidates_df.get_column("formula").to_list():
        # Skip all rules for ionization peaks
        return (
            candidates_df.filter(pl.col("formula") == "()").to_dicts(),
            log_messages,
        )

    for i, rule in enumerate(HEURISTIC_RULES):
        if candidates_df.is_empty():
            log_messages.append(
                f"No candidates passed the rule: {HEURISTIC_RULES[i - 1].__name__}"
            )
            break
        rule_mask, rule_log_messages = rule(
            candidates_df, heuristics_config=heuristics_config
        )
        log_messages.extend(rule_log_messages)
        candidates_df = candidates_df.filter(rule_mask)

    return candidates_df.to_dicts(), log_messages


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
    if "()" in candidates_df.get_column("formula").to_list():
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


def _custom_isotope_combinations(
    symbol: str, count: int, purity: float
) -> list[tuple[float, float, int]]:
    """Multinomial isotope combinations for `count` atoms of a labelled '^X'
    (two-isotope) element. Returns [(added_mass, probability, n_light), ...]."""
    from math import comb

    isos = _CUSTOM_ELEMENT_DATA[symbol][1]
    (m_light, _), (m_heavy, _) = isos[0], isos[-1]
    p_heavy, p_light = purity, 1.0 - purity
    out = []
    for k in range(count + 1):  # k = number of heavy (labelled) atoms
        n_light = count - k
        prob = comb(count, k) * p_heavy**k * p_light**n_light
        out.append((k * m_heavy + n_light * m_light, prob, n_light))
    return out


def _predict_isotopes_custom(
    ion_formula: str, ion_charge: int, purity: float
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """predict_isotopes for an ion containing labelled '^X' custom elements: base
    (non-custom) envelope via IsoSpec, convolved with the labelled distribution(s)
    (multinomial; Cartesian product for several). Most-abundant peak first."""
    import itertools

    from mascope_tools.composition.utils import parse_composition, to_hill_order

    comp = parse_composition(ion_formula)
    customs = {s: int(comp[s]) for s in comp if s.startswith("^")}
    base = {s: int(comp[s]) for s in comp if not s.startswith("^") and comp[s] > 0}
    base_formula = to_hill_order(base) if base else ""

    if base_formula:
        peaks = IsoThreshold(
            formula=base_formula, threshold=ISOTOPE_ABUNDANCE_THRESHOLD, get_confs=True
        )
        base_masses = [float(m) for m in peaks.masses]
        base_probs = [float(p) for p in peaks.probs]
        base_labels = extract_isotope_labels(base_formula, peaks)
    else:
        base_masses, base_probs, base_labels = [0.0], [1.0], ["M0"]

    combos_per_element = [
        [
            (
                mass,
                prob,
                n_light,
                _CUSTOM_ELEMENT_DATA[sym][0],
                _CUSTOM_ELEMENT_DATA[sym][1][0][1],
            )
            for (mass, prob, n_light) in _custom_isotope_combinations(sym, cnt, purity)
        ]
        for sym, cnt in customs.items()
    ]

    merged: dict[float, list] = {}
    for bm, bp, bl in zip(base_masses, base_probs, base_labels):
        for combo in itertools.product(*combos_per_element):
            mass = bm + sum(c[0] for c in combo)
            prob = bp
            for c in combo:
                prob *= c[1]
            if prob < ISOTOPE_ABUNDANCE_THRESHOLD:
                continue
            deviations = [
                f"{light_mn}{regular}" + (str(n_light) if n_light > 1 else "")
                for (_, _, n_light, regular, light_mn) in combo
                if n_light
            ]
            parts = ([] if bl in ("M0", "", "---") else [bl]) + deviations
            label = "+".join(parts) if parts else "M0"
            key = round(mass, 4)
            if key in merged:
                m0, p0, _ = merged[key]
                tot = p0 + prob
                merged[key][0] = (m0 * p0 + mass * prob) / tot
                merged[key][1] = tot
            else:
                merged[key] = [mass, prob, label]

    items = sorted(merged.values(), key=lambda x: -x[1])  # most-abundant first
    mzs = np.array(
        [(m - ELECTRON_MASS * ion_charge) / abs(ion_charge) for m, _, _ in items]
    )
    probs = np.array([p for _, p, _ in items])
    labels = [lab for _, _, lab in items]
    return mzs, probs, labels


def predict_isotopes(
    ion_formula: str, ion_charge: int, purity: float | None = None
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Predict isotopic pattern for a given ion formula and charge.

    :param ion_formula: Ion formula string (may contain labelled '^X' elements).
    :type ion_formula: str
    :param ion_charge: Ion charge (e.g., +1, -1).
    :type ion_charge: int
    :param purity: Isotopic purity of labelled '^X' elements (heaviest-isotope
        fraction, e.g. 0.98 for a 98% 15N reagent). A property of the labelled
        reagent; the caller passes its value. Ignored for non-labelled ions.
        Defaults to ``LABELLED_REAGENT_PURITY``.
    :type purity: float, optional
    :return: Tuple of predicted m/z values, relative intensities, and isotope labels.
    :rtype: tuple[np.ndarray, np.ndarray, list[str]]
    """
    if "^" in ion_formula:
        try:
            return _predict_isotopes_custom(
                ion_formula,
                ion_charge,
                LABELLED_REAGENT_PURITY if purity is None else purity,
            )
        except Exception:
            return [], [], []
    try:
        predicted_peaks = IsoThreshold(
            formula=ion_formula,
            threshold=ISOTOPE_ABUNDANCE_THRESHOLD,
            get_confs=True,
        )
        predicted_masses_neutral = np.fromiter(predicted_peaks.masses, dtype=float)
        predicted_intensities = np.fromiter(predicted_peaks.probs, dtype=float)
        isotope_labels = extract_isotope_labels(ion_formula, predicted_peaks)
        # Convert neutral masses to m/z
        predicted_mzs = (predicted_masses_neutral - ELECTRON_MASS * ion_charge) / abs(
            ion_charge
        )
    except Exception:
        predicted_mzs, predicted_intensities, isotope_labels = [], [], []

    return predicted_mzs, predicted_intensities, isotope_labels


def extract_isotope_labels(
    ion_formula: str, predicted_isotopes: IsoDistribution
) -> list[str]:
    """Convert isotope configurations to labels.
    Requires IsoDistribution with confs.

    Examples:
        >>> extract_isotope_labels(
        ...     "C6H12O6",
        ...     IsoThreshold(
        ...         formula="C6H12O6",
        ...         threshold=ISOTOPE_ABUNDANCE_THRESHOLD,
        ...         get_confs=True
        ...     )
        ... )
        ['M0', '13C', '18O']

    :param ion_formula: Ion formula string.
    :type ion_formula: str
    :param predicted_isotopes: Predicted isotope distribution.
    :type predicted_isotopes: IsoDistribution
    :return: List of isotope labels.
    :rtype: list[str]
    """
    if ion_formula.endswith(("+", "-")):
        # Remove charge character for parsing
        ion_formula = ion_formula[:-1]
    try:
        composition = Composition(formula=to_pyteomics(ion_formula))
        elements = list(composition.keys())
        elemental_masses = [PeriodicTbl.symbol_to_masses[el] for el in elements]
        isotope_labels = [
            conf_to_label(conf, elements, elemental_masses)
            for conf in predicted_isotopes.confs
        ]
    except AttributeError:
        raise AttributeError(
            "Predicted isotopes must include configurations (confs) for label extraction."
        )
    return isotope_labels


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


# ---------------------------------------------------------------------------
# Match score, version 2 (detectability-gated, SNR-aware, calibratable).
#
# v1 (`score_pattern`, above) averages errors over the MATCHED peaks only, so an
# incomplete isotope envelope is not penalised, and it normalises mass by a fixed
# 5 ppm. v2 fixes both: it penalises a predicted isotopologue that is ABSENT but
# should have been visible (expected SNR `rel_i*SNR_base >= k_detect`), judges each
# isotopologue's intensity against ITS OWN noise (per-peak SNR), uses a Gaussian
# mass likelihood, and aggregates as a predicted-abundance-weighted geometric mean.
# On the demo golden set vs v1: ROC-AUC 0.876->0.890, held-out calibrated ECE
# 0.020->0.0069 (see tooling/score_eval/DESIGN.md). v1 is retained byte-identical;
# callers select via SCORE_VERSION. Inputs use the same matched-array convention as
# v1 (unmatched isotopologues carry 0), PLUS the matched peaks' signal_to_noise.
# ---------------------------------------------------------------------------
SCORE_VERSION = 2

# Mass-error Gaussian width used ONLY when the caller does not supply the
# instrument's fitted mass accuracy. The mass term is `exp(-0.5*(ppm/sigma)^2)`, so
# `sigma_ppm` must match the instrument: ~0.5-2 ppm for an Orbitrap, ~5-10 ppm for a
# TOF. This fallback is Orbitrap-appropriate and is WRONG for a TOF (it would tank
# valid low-resolution matches) — pass the per-sample fitted sigma instead.
FALLBACK_SIGMA_PPM = 2.0

# Platt calibration (raw fit score -> P(correct)) fitted on the demo Br/Ur golden
# set. Maps a raw v2 score to a probability; refit per instrument/dataset with the
# score_eval harness (DESIGN.md §5.3) for production — a sensible default, not a
# universal constant.
DEFAULT_CALIBRATION_V2 = (6.0546, -4.1481)  # (a, b) fit on the demo Br/Ur golden set


def calibrate_score(raw, calibration=None):
    """Map a raw v2 score to a probability via `sigmoid(a*raw + b)`."""
    a, b = calibration or DEFAULT_CALIBRATION_V2
    return 1.0 / (1.0 + np.exp(-(a * np.asarray(raw, float) + b)))


def score_pattern_v2(
    observed_mass_errors_ppm: np.ndarray,
    observed_intensities: np.ndarray,
    observed_snr: np.ndarray,
    predicted_rel: np.ndarray,
    *,
    k_detect: float = 3.0,
    miss_penalty: float = 0.3,
    sigma_ppm: float | None = None,
) -> float:
    """Detectability-gated, SNR-aware match score in [0, 1].

    Per predicted isotopologue i (predicted relative abundance `predicted_rel[i]`,
    base = index 0): a matched peak contributes a Gaussian mass likelihood times an
    intensity likelihood whose tolerance is set by the peak's own SNR; an ABSENT
    peak contributes `miss_penalty` iff it should have been detectable
    (`predicted_rel[i]*SNR_base >= k_detect`), else it is excluded (below noise, not
    evidence). Aggregation is a predicted-abundance-weighted geometric mean. Returns
    0 if the monoisotopic peak is absent. Satellite peaks must be excluded by the
    caller. Pair with `calibrate_score` to get P(correct).

    `sigma_ppm` is the instrument's mass-error std (the mass-term width); pass the
    fitted per-sample value so the score is resolution-correct (Orbitrap vs TOF).
    `observed_mass_errors_ppm` should be offset-centred (subtract the fitted mu).
    When `sigma_ppm` is None, `FALLBACK_SIGMA_PPM` is used — Orbitrap-only; see it."""
    if sigma_ppm is None:
        sigma_ppm = FALLBACK_SIGMA_PPM
    oi = np.asarray(observed_intensities, float)
    if len(oi) == 0 or oi[0] <= 0:
        return 0.0
    me = np.abs(np.asarray(observed_mass_errors_ppm, float))
    snr = np.maximum(np.asarray(observed_snr, float), 1e-6)
    pr = np.asarray(predicted_rel, float)
    base_int, base_snr = oi[0], snr[0]
    n = len(pr)

    matched = oi > 0
    mass_L = np.exp(-0.5 * (me / sigma_ppm) ** 2)
    rel_obs = oi / base_int
    sigma_rel = np.maximum.reduce(
        [
            rel_obs * np.sqrt(1.0 / snr**2 + 1.0 / base_snr**2),
            0.05 * pr,
            np.full(n, 1e-3),
        ]
    )
    int_L = np.exp(-0.5 * ((rel_obs - pr) / sigma_rel) ** 2)

    L = np.full(n, np.nan)
    L[0] = mass_L[0]
    m = matched.copy()
    m[0] = False
    L[m] = mass_L[m] * int_L[m]
    absent = ~matched
    absent[0] = False
    detectable = absent & (pr * base_snr >= k_detect)
    L[detectable] = miss_penalty
    include = ~np.isnan(L)
    L = np.where(include, np.maximum(L, 1e-6), 1.0)
    w = pr * include
    wsum = w.sum()
    if wsum <= 0:
        return 0.0
    return float(np.exp((w * np.log(L)).sum() / wsum))


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
