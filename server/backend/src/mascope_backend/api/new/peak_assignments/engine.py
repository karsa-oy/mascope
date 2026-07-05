"""
Pure transformation logic for peak-centric assignment.

Inverts target-anchored match results (one row per target isotope) into
peak-anchored assignments (one row per observed peak), applies the
single-owner-per-peak arbitration, and maps untargeted composition-finder
results onto the same row shape.

No database access happens here - everything is DataFrame/dict manipulation
so the arbitration logic stays unit-testable. The service layer owns
persistence.
"""

import numpy as np
import pandas as pd

from mascope_backend.db.id import gen_id


# Confidence tiers (a richer replacement for match_category 0/1/2)
TIER_IDENTIFIED = "identified"
TIER_CANDIDATE = "candidate"
TIER_BELOW_ASSIGNABILITY = "below_assignability"
TIER_UNASSIGNED = "unassigned"

# Peak roles within an assignment run
ROLE_M0 = "M0"
ROLE_ISO_CHILD = "iso_child"
ROLE_UNASSIGNED = "unassigned"

# Which stage won the peak
SOURCE_DATABASE = "database"
SOURCE_UNTARGETED = "untargeted"

# Placeholder used by the untargeted finder for unassigned peaks
UNTARGETED_NO_MATCH = "---"
# The finder emits "()" for ionization/reagent peaks (an adduct with no
# molecular core). That is not a molecular formula, so it must not be persisted
# as one; a dedicated reagent role is a later phase.
UNTARGETED_IONIZATION = "()"


def tier_for_score(
    score: float | None,
    possible_threshold: float,
    probable_threshold: float,
) -> str:
    """Map a match score onto a confidence tier."""
    if score is None or not np.isfinite(score) or score <= 0:
        return TIER_BELOW_ASSIGNABILITY
    if score >= probable_threshold:
        return TIER_IDENTIFIED
    if score >= possible_threshold:
        return TIER_CANDIDATE
    return TIER_BELOW_ASSIGNABILITY


def _float_or_none(value) -> float | None:
    """Coerce to float, mapping NaN/None/missing to None."""
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if np.isfinite(value) else None


def _score_or_none(value) -> float | None:
    """Coerce a match score to float within [0, 1], or None."""
    score = _float_or_none(value)
    if score is None:
        return None
    return min(1.0, max(0.0, score))


def _str_or_none(value) -> str | None:
    """Coerce to str, mapping NaN/None to None."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    return str(value)


def _isotope_offset_label(iso_mz: float, main_mz: float | None) -> str | None:
    """Label an isotopologue by its nominal mass offset from the ion's M0."""
    if main_mz is None or not np.isfinite(main_mz):
        return None
    offset = int(round(iso_mz - main_mz))
    if offset == 0:
        return "M0"
    return f"M+{offset}" if offset > 0 else f"M{offset}"


def invert_matches_to_peak_assignments(
    match_isotope_df: pd.DataFrame,
    sample_item_id: str,
    peak_assignment_run_id: str,
    possible_threshold: float,
    probable_threshold: float,
    max_alternatives: int = 5,
) -> list[dict]:
    """Invert target-first match results into per-peak assignments (Stage A).

    The targeted matcher produces one row per target isotope with the
    sample_peak_id it hit (or a placeholder when unmatched). This groups those
    rows by peak, picks the best-scoring owner per peak (ties broken by
    smaller m/z error), and keeps the runners-up as alternatives - the
    single-owner-per-peak invariant.

    Roles: the winner is 'M0' when it is its ion's reference (most abundant)
    isotope, otherwise 'iso_child' pointing at the assignment that holds the
    ion's M0 peak (when that peak was also won by the same ion).

    :param match_isotope_df: Output of compute_match_isotopes enriched with
        target metadata columns (target_compound_id, target_compound_formula,
        target_ion_formula, ionization_mechanism_id).
    :param sample_item_id: Sample the peaks belong to.
    :param peak_assignment_run_id: Run the assignments belong to.
    :param possible_threshold: Score threshold for the 'candidate' tier.
    :param probable_threshold: Score threshold for the 'identified' tier.
    :param max_alternatives: Cap on stored runner-up candidates per peak.
    :return: One assignment dict per matched peak, ready for bulk insert.
    """
    if match_isotope_df.empty:
        return []

    matched = match_isotope_df[
        match_isotope_df["sample_peak_id"].notna()
        & (match_isotope_df["sample_peak_id"] != "")
    ].copy()
    if matched.empty:
        return []

    # Reference (most abundant) isotope per ion, used for role attribution
    # and isotope labelling. Computed over the full target set so an ion
    # whose M0 went unmatched still labels its children correctly.
    main_idx = match_isotope_df.groupby("target_ion_id")["relative_abundance"].idxmax()
    main_isotopes = match_isotope_df.loc[main_idx]
    main_isotope_ids = set(main_isotopes["target_isotope_id"])
    main_mz_by_ion = main_isotopes.set_index("target_ion_id")["mz"].to_dict()

    matched["_abs_mz_error"] = matched["match_mz_error"].abs()
    matched = matched.sort_values(
        ["sample_peak_id", "match_score", "_abs_mz_error"],
        ascending=[True, False, True],
    )

    assignments: list[dict] = []
    m0_assignment_by_ion: dict[str, str] = {}
    child_assignments: list[tuple[dict, str]] = []

    for sample_peak_id, group in matched.groupby("sample_peak_id", sort=False):
        winner = group.iloc[0]
        runners = (
            group.iloc[1 : 1 + max_alternatives]
            if max_alternatives
            else group.iloc[1:1]
        )
        alternatives = [
            {
                "assigned_formula": _str_or_none(row.get("target_compound_formula")),
                "ion_formula": _str_or_none(row.get("target_ion_formula")),
                "target_compound_id": _str_or_none(row.get("target_compound_id")),
                "target_ion_id": _str_or_none(row.get("target_ion_id")),
                "match_score": _score_or_none(row.get("match_score")),
                "mz_error_ppm": _float_or_none(row.get("match_mz_error")),
                "source": SOURCE_DATABASE,
            }
            for _, row in runners.iterrows()
        ]

        ion_id = _str_or_none(winner.get("target_ion_id"))
        is_main = winner["target_isotope_id"] in main_isotope_ids
        isotope_label = (
            "M0"
            if is_main
            else _isotope_offset_label(winner["mz"], main_mz_by_ion.get(ion_id))
        )

        assignment = {
            "peak_assignment_id": gen_id(32),
            "peak_assignment_run_id": peak_assignment_run_id,
            "sample_item_id": sample_item_id,
            "sample_peak_id": str(sample_peak_id),
            "sample_peak_mz": float(winner["sample_peak_mz"]),
            "sample_peak_intensity": float(winner["sample_peak_intensity"]),
            "sample_peak_tof": _float_or_none(winner.get("sample_peak_tof")),
            "role": ROLE_M0 if is_main else ROLE_ISO_CHILD,
            "assigned_formula": _str_or_none(winner.get("target_compound_formula")),
            "ion_formula": _str_or_none(winner.get("target_ion_formula")),
            "ionization_mechanism_id": _str_or_none(
                winner.get("ionization_mechanism_id")
            ),
            "isotope_label": isotope_label,
            "source": SOURCE_DATABASE,
            "match_score": _score_or_none(winner["match_score"]),
            "mz_error_ppm": _float_or_none(winner["match_mz_error"]),
            "abundance_error": _float_or_none(winner["match_abundance_error"]),
            "tier": tier_for_score(
                _score_or_none(winner["match_score"]),
                possible_threshold,
                probable_threshold,
            ),
            "target_compound_id": _str_or_none(winner.get("target_compound_id")),
            "target_ion_id": ion_id,
            "owner_peak_assignment_id": None,
            "alternatives": alternatives or None,
            "provenance": None,
        }
        assignments.append(assignment)

        if is_main and ion_id is not None:
            m0_assignment_by_ion[ion_id] = assignment["peak_assignment_id"]
        else:
            child_assignments.append((assignment, ion_id))

    # Attribute isotope children to their ion's M0 assignment. Stays None
    # when the ion's M0 peak was not won by the same ion in this run.
    for assignment, ion_id in child_assignments:
        assignment["owner_peak_assignment_id"] = m0_assignment_by_ion.get(ion_id)

    return assignments


def untargeted_matches_to_peak_assignments(
    matches_df: pd.DataFrame,
    peak_lookup: dict[float, tuple[str, float]],
    sample_item_id: str,
    peak_assignment_run_id: str,
    possible_threshold: float,
    probable_threshold: float,
    mechanism_id_by_notation: dict[str, str] | None = None,
    formula_formatter=None,
) -> list[dict]:
    """Map untargeted composition results onto peak assignments (Stage B).

    `assign_compositions` already yields one row per input peak with the best
    composition, isotope labelling, and runner-up formulas; this converts
    those rows into the persisted PeakAssignment shape. Rows with the '---'
    placeholder are skipped (their peaks stay unassigned).

    The Stage B score reuses the targeted matcher's maths:
    ``score = (1 - min(1, |intensity_error|)) * max(0, 1 - |mz_error_ppm|/100)``
    with the abundance term dropped when no isotope envelope was evaluated.

    :param matches_df: First element returned by assign_compositions.
    :param peak_lookup: Maps peak m/z -> (sample_peak_id, intensity) for the
        peaks that were fed into the untargeted search.
    :param mechanism_id_by_notation: Maps the ionization notation used in the
        search back to IonizationMechanism ids.
    :param formula_formatter: Optional callable applied to formulas (e.g.
        explicit-isotope to custom element notation conversion).
    :return: One assignment dict per assigned peak, ready for bulk insert.
    """
    if matches_df.empty:
        return []

    mechanism_id_by_notation = mechanism_id_by_notation or {}
    format_formula = formula_formatter or (lambda formula: formula)

    assignments: list[dict] = []
    m0_assignment_by_group: dict[tuple, str] = {}
    child_assignments: list[tuple[dict, tuple]] = []
    seen_peak_ids: set[str] = set()

    for _, row in matches_df.iterrows():
        formula = row.get("formula")
        if not isinstance(formula, str) or formula in (
            UNTARGETED_NO_MATCH,
            UNTARGETED_IONIZATION,
        ):
            continue

        peak = peak_lookup.get(float(row["mz"]))
        if peak is None:
            # Isotope children can land on m/z values outside the peaks fed
            # to the search (e.g. below the intensity threshold); there is no
            # observed peak row to assign in that case.
            continue
        sample_peak_id, intensity = peak
        if sample_peak_id in seen_peak_ids:
            continue
        seen_peak_ids.add(sample_peak_id)

        # Fall back to composition_error_ppm when mz_error_ppm is absent OR
        # present-but-NaN. dict.get's default only covers the absent case, so a
        # NaN in a mixed batch (some rows carry an isotope-envelope mz error,
        # some do not) would otherwise collapse the score to 0.
        mz_error_ppm = _float_or_none(row.get("mz_error_ppm"))
        if mz_error_ppm is None:
            mz_error_ppm = _float_or_none(row.get("composition_error_ppm"))
        abundance_error = _float_or_none(row.get("intensity_error"))

        mz_term = (
            max(0.0, 1.0 - 1e-2 * abs(mz_error_ppm))
            if mz_error_ppm is not None
            else 0.0
        )
        abundance_term = (
            1.0 - min(1.0, abs(abundance_error)) if abundance_error is not None else 1.0
        )
        score = abundance_term * mz_term

        isotope_label = _str_or_none(row.get("isotope_label")) or "M0"
        is_m0 = isotope_label == "M0"
        notation = _str_or_none(row.get("ionization_mechanism"))
        group_key = (formula, notation)

        other_candidates = _str_or_none(row.get("other_candidates"))
        alternatives = (
            [
                {
                    "assigned_formula": format_formula(alt.strip()),
                    "source": SOURCE_UNTARGETED,
                }
                for alt in other_candidates.split(",")
                if alt.strip()
            ]
            if other_candidates
            else None
        )

        provenance = {
            key: _float_or_none(row.get(key))
            for key in ("neutral_mass", "unsaturation")
            if _float_or_none(row.get(key)) is not None
        }

        assignment = {
            "peak_assignment_id": gen_id(32),
            "peak_assignment_run_id": peak_assignment_run_id,
            "sample_item_id": sample_item_id,
            "sample_peak_id": sample_peak_id,
            "sample_peak_mz": float(row["mz"]),
            "sample_peak_intensity": float(intensity),
            "sample_peak_tof": None,
            "role": ROLE_M0 if is_m0 else ROLE_ISO_CHILD,
            "assigned_formula": format_formula(formula),
            "ion_formula": _str_or_none(row.get("ion")),
            "ionization_mechanism_id": mechanism_id_by_notation.get(notation),
            "isotope_label": isotope_label,
            "source": SOURCE_UNTARGETED,
            "match_score": _score_or_none(score),
            "mz_error_ppm": mz_error_ppm,
            "abundance_error": abundance_error,
            "tier": tier_for_score(score, possible_threshold, probable_threshold),
            "target_compound_id": None,
            "target_ion_id": None,
            "owner_peak_assignment_id": None,
            "alternatives": alternatives,
            "provenance": provenance or None,
        }
        assignments.append(assignment)

        if is_m0:
            m0_assignment_by_group.setdefault(
                group_key, assignment["peak_assignment_id"]
            )
        else:
            child_assignments.append((assignment, group_key))

    for assignment, group_key in child_assignments:
        assignment["owner_peak_assignment_id"] = m0_assignment_by_group.get(group_key)

    return assignments


def build_unassigned_assignments(
    peaks_df: pd.DataFrame,
    sample_item_id: str,
    peak_assignment_run_id: str,
) -> list[dict]:
    """Build placeholder rows for peaks no stage explained.

    Every observed peak gets exactly one row per run; peaks left over after
    Stage A and Stage B are persisted with role/tier 'unassigned' so the
    ledger is complete and queryable.

    :param peaks_df: DataFrame with sample_peak_id, mz, and intensity columns.
    """
    return [
        {
            "peak_assignment_id": gen_id(32),
            "peak_assignment_run_id": peak_assignment_run_id,
            "sample_item_id": sample_item_id,
            "sample_peak_id": str(row.sample_peak_id),
            "sample_peak_mz": float(row.mz),
            "sample_peak_intensity": float(row.intensity),
            "sample_peak_tof": None,
            "role": ROLE_UNASSIGNED,
            "assigned_formula": None,
            "ion_formula": None,
            "ionization_mechanism_id": None,
            "isotope_label": None,
            "source": None,
            "match_score": None,
            "mz_error_ppm": None,
            "abundance_error": None,
            "tier": TIER_UNASSIGNED,
            "target_compound_id": None,
            "target_ion_id": None,
            "owner_peak_assignment_id": None,
            "alternatives": None,
            "provenance": None,
        }
        for row in peaks_df.itertuples(index=False)
    ]
