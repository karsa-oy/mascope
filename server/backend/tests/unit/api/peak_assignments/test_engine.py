"""
Unit tests for the peak-centric assignment engine.

Covers the target-to-peak inversion (Stage A), the single-owner-per-peak
arbitration, isotope-child attribution, confidence tiers, and the mapping of
untargeted composition results onto assignment rows (Stage B). Pure
DataFrame/dict logic - no database access.
"""

import pandas as pd
import pytest

from mascope_backend.api.new.peak_assignments.engine import (
    ROLE_ISO_CHILD,
    ROLE_M0,
    ROLE_UNASSIGNED,
    SOURCE_DATABASE,
    SOURCE_UNTARGETED,
    TIER_BELOW_ASSIGNABILITY,
    TIER_CANDIDATE,
    TIER_IDENTIFIED,
    TIER_UNASSIGNED,
    build_unassigned_assignments,
    invert_matches_to_peak_assignments,
    tier_for_score,
    untargeted_matches_to_peak_assignments,
)


POSSIBLE = 0.7
PROBABLE = 0.8


def _isotope_row(
    *,
    target_isotope_id: str,
    target_ion_id: str,
    target_compound_id: str,
    compound_formula: str,
    ion_formula: str,
    mz: float,
    relative_abundance: float,
    sample_peak_id: str,
    sample_peak_mz: float | None = None,
    sample_peak_intensity: float = 1000.0,
    match_score: float = 0.9,
    match_mz_error: float = 1.0,
    match_abundance_error: float = 0.05,
) -> dict:
    """One row of the targeted matcher's output enriched with target metadata."""
    return {
        "target_isotope_id": target_isotope_id,
        "target_ion_id": target_ion_id,
        "target_isotope_formula": compound_formula,
        "mz": mz,
        "relative_abundance": relative_abundance,
        "resolution": "HIGH",
        "target_ion_formula": ion_formula,
        "ionization_mechanism_id": "mech1",
        "target_compound_id": target_compound_id,
        "target_compound_formula": compound_formula,
        "sample_peak_id": sample_peak_id,
        "sample_peak_mz": sample_peak_mz if sample_peak_mz is not None else mz,
        "sample_peak_intensity": sample_peak_intensity,
        "sample_peak_tof": 12.3,
        "match_score": match_score,
        "match_mz_error": match_mz_error,
        "match_abundance_error": match_abundance_error,
    }


class TestTierForScore:
    def test_probable_score_is_identified(self):
        assert tier_for_score(0.85, POSSIBLE, PROBABLE) == TIER_IDENTIFIED

    def test_threshold_boundaries_are_inclusive(self):
        assert tier_for_score(PROBABLE, POSSIBLE, PROBABLE) == TIER_IDENTIFIED
        assert tier_for_score(POSSIBLE, POSSIBLE, PROBABLE) == TIER_CANDIDATE

    def test_possible_score_is_candidate(self):
        assert tier_for_score(0.75, POSSIBLE, PROBABLE) == TIER_CANDIDATE

    def test_weak_score_is_below_assignability(self):
        assert tier_for_score(0.3, POSSIBLE, PROBABLE) == TIER_BELOW_ASSIGNABILITY

    def test_zero_and_missing_scores_are_below_assignability(self):
        assert tier_for_score(0.0, POSSIBLE, PROBABLE) == TIER_BELOW_ASSIGNABILITY
        assert tier_for_score(None, POSSIBLE, PROBABLE) == TIER_BELOW_ASSIGNABILITY
        assert tier_for_score(float("nan"), POSSIBLE, PROBABLE) == (
            TIER_BELOW_ASSIGNABILITY
        )


class TestInvertMatches:
    def test_empty_input_yields_no_assignments(self):
        assert (
            invert_matches_to_peak_assignments(
                pd.DataFrame(), "sample1", "run1", POSSIBLE, PROBABLE
            )
            == []
        )

    def test_best_score_wins_contested_peak_and_loser_becomes_alternative(self):
        match_df = pd.DataFrame(
            [
                _isotope_row(
                    target_isotope_id="iso1",
                    target_ion_id="ion1",
                    target_compound_id="cmp1",
                    compound_formula="C6H12O6",
                    ion_formula="C6H13O6+",
                    mz=181.0707,
                    relative_abundance=1.0,
                    sample_peak_id="p1",
                    match_score=0.95,
                ),
                _isotope_row(
                    target_isotope_id="iso3",
                    target_ion_id="ion2",
                    target_compound_id="cmp2",
                    compound_formula="C7H16O5",
                    ion_formula="C7H17O5+",
                    mz=181.0705,
                    relative_abundance=1.0,
                    sample_peak_id="p1",
                    match_score=0.75,
                ),
            ]
        )

        assignments = invert_matches_to_peak_assignments(
            match_df, "sample1", "run1", POSSIBLE, PROBABLE
        )

        assert len(assignments) == 1
        winner = assignments[0]
        assert winner["sample_peak_id"] == "p1"
        assert winner["assigned_formula"] == "C6H12O6"
        assert winner["target_compound_id"] == "cmp1"
        assert winner["target_ion_id"] == "ion1"
        assert winner["source"] == SOURCE_DATABASE
        assert winner["role"] == ROLE_M0
        assert winner["tier"] == TIER_IDENTIFIED
        assert winner["peak_assignment_run_id"] == "run1"
        assert winner["sample_item_id"] == "sample1"

        # The losing candidate is preserved as an alternative
        assert len(winner["alternatives"]) == 1
        assert winner["alternatives"][0]["target_ion_id"] == "ion2"
        assert winner["alternatives"][0]["assigned_formula"] == "C7H16O5"
        assert winner["alternatives"][0]["match_score"] == pytest.approx(0.75)

    def test_isotope_child_points_at_its_ions_m0_assignment(self):
        match_df = pd.DataFrame(
            [
                _isotope_row(
                    target_isotope_id="iso1",
                    target_ion_id="ion1",
                    target_compound_id="cmp1",
                    compound_formula="C6H12O6",
                    ion_formula="C6H13O6+",
                    mz=181.0707,
                    relative_abundance=1.0,
                    sample_peak_id="p1",
                    match_score=0.95,
                ),
                _isotope_row(
                    target_isotope_id="iso2",
                    target_ion_id="ion1",
                    target_compound_id="cmp1",
                    compound_formula="C6H12O6",
                    ion_formula="C6H13O6+",
                    mz=182.0741,
                    relative_abundance=0.065,
                    sample_peak_id="p2",
                    match_score=0.85,
                ),
            ]
        )

        assignments = invert_matches_to_peak_assignments(
            match_df, "sample1", "run1", POSSIBLE, PROBABLE
        )
        by_peak = {a["sample_peak_id"]: a for a in assignments}

        m0 = by_peak["p1"]
        child = by_peak["p2"]
        assert m0["role"] == ROLE_M0
        assert m0["isotope_label"] == "M0"
        assert m0["owner_peak_assignment_id"] is None
        assert child["role"] == ROLE_ISO_CHILD
        assert child["isotope_label"] == "M+1"
        assert child["owner_peak_assignment_id"] == m0["peak_assignment_id"]

    def test_child_owner_stays_none_when_ions_m0_lost_its_peak(self):
        # ion1's M0 loses peak p1 to ion2, but ion1's M+1 still wins p2:
        # the child cannot be attributed to an M0 assignment of its own ion.
        match_df = pd.DataFrame(
            [
                _isotope_row(
                    target_isotope_id="iso1",
                    target_ion_id="ion1",
                    target_compound_id="cmp1",
                    compound_formula="C6H12O6",
                    ion_formula="C6H13O6+",
                    mz=181.0707,
                    relative_abundance=1.0,
                    sample_peak_id="p1",
                    match_score=0.6,
                ),
                _isotope_row(
                    target_isotope_id="iso2",
                    target_ion_id="ion1",
                    target_compound_id="cmp1",
                    compound_formula="C6H12O6",
                    ion_formula="C6H13O6+",
                    mz=182.0741,
                    relative_abundance=0.065,
                    sample_peak_id="p2",
                    match_score=0.75,
                ),
                _isotope_row(
                    target_isotope_id="iso3",
                    target_ion_id="ion2",
                    target_compound_id="cmp2",
                    compound_formula="C7H16O5",
                    ion_formula="C7H17O5+",
                    mz=181.0705,
                    relative_abundance=1.0,
                    sample_peak_id="p1",
                    match_score=0.9,
                ),
            ]
        )

        assignments = invert_matches_to_peak_assignments(
            match_df, "sample1", "run1", POSSIBLE, PROBABLE
        )
        by_peak = {a["sample_peak_id"]: a for a in assignments}

        assert by_peak["p1"]["target_ion_id"] == "ion2"
        child = by_peak["p2"]
        assert child["target_ion_id"] == "ion1"
        assert child["role"] == ROLE_ISO_CHILD
        assert child["owner_peak_assignment_id"] is None
        assert child["tier"] == TIER_CANDIDATE

    def test_unmatched_isotopes_are_ignored(self):
        match_df = pd.DataFrame(
            [
                _isotope_row(
                    target_isotope_id="iso1",
                    target_ion_id="ion1",
                    target_compound_id="cmp1",
                    compound_formula="C6H12O6",
                    ion_formula="C6H13O6+",
                    mz=181.0707,
                    relative_abundance=1.0,
                    sample_peak_id="",  # matcher placeholder for unmatched
                    match_score=0.0,
                ),
            ]
        )
        assert (
            invert_matches_to_peak_assignments(
                match_df, "sample1", "run1", POSSIBLE, PROBABLE
            )
            == []
        )

    def test_alternatives_are_capped(self):
        rows = [
            _isotope_row(
                target_isotope_id=f"iso{i}",
                target_ion_id=f"ion{i}",
                target_compound_id=f"cmp{i}",
                compound_formula="C6H12O6",
                ion_formula="C6H13O6+",
                mz=181.0707,
                relative_abundance=1.0,
                sample_peak_id="p1",
                match_score=0.9 - i * 0.05,
            )
            for i in range(6)
        ]
        assignments = invert_matches_to_peak_assignments(
            pd.DataFrame(rows),
            "sample1",
            "run1",
            POSSIBLE,
            PROBABLE,
            max_alternatives=2,
        )
        assert len(assignments) == 1
        assert len(assignments[0]["alternatives"]) == 2


class TestUntargetedMatches:
    def _matches_df(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "mz": 100.1,
                    "formula": "C5H10O2",
                    "ion": "C5H11O2+",
                    "isotope_label": "M0",
                    "ionization_mechanism": "+H+",
                    "mz_error_ppm": 2.0,
                    "intensity_error": 0.1,
                    "other_candidates": "C4H8N2O, C6H14N",
                    "neutral_mass": 102.068,
                    "unsaturation": 1.0,
                },
                {
                    "mz": 101.1033,
                    "formula": "C5H10O2",
                    "ion": "[13C]C4H11O2+",
                    "isotope_label": "13C",
                    "ionization_mechanism": "+H+",
                    "mz_error_ppm": 3.0,
                    "intensity_error": 0.2,
                    "other_candidates": "",
                    "neutral_mass": 103.071,
                    "unsaturation": 1.0,
                },
                {
                    "mz": 102.2,
                    "formula": "---",
                    "ion": "---",
                    "isotope_label": "---",
                    "other_candidates": "",
                },
            ]
        )

    def _peak_lookup(self) -> dict:
        return {
            100.1: ("pA", 5000.0),
            101.1033: ("pB", 300.0),
            102.2: ("pC", 50.0),
        }

    def test_assigned_rows_map_to_assignments_and_placeholder_is_skipped(self):
        assignments = untargeted_matches_to_peak_assignments(
            self._matches_df(),
            self._peak_lookup(),
            "sample1",
            "run1",
            POSSIBLE,
            PROBABLE,
            mechanism_id_by_notation={"+H+": "mech1"},
        )

        assert len(assignments) == 2
        by_peak = {a["sample_peak_id"]: a for a in assignments}
        assert set(by_peak) == {"pA", "pB"}

        m0 = by_peak["pA"]
        assert m0["role"] == ROLE_M0
        assert m0["source"] == SOURCE_UNTARGETED
        assert m0["assigned_formula"] == "C5H10O2"
        assert m0["ionization_mechanism_id"] == "mech1"
        assert m0["target_compound_id"] is None
        # score = (1 - 0.1) * (1 - 2.0/100)
        assert m0["match_score"] == pytest.approx(0.9 * 0.98)
        assert m0["tier"] == TIER_IDENTIFIED
        assert [alt["assigned_formula"] for alt in m0["alternatives"]] == [
            "C4H8N2O",
            "C6H14N",
        ]
        assert m0["provenance"]["neutral_mass"] == pytest.approx(102.068)

    def test_isotope_child_is_attributed_to_its_formula_group_m0(self):
        assignments = untargeted_matches_to_peak_assignments(
            self._matches_df(),
            self._peak_lookup(),
            "sample1",
            "run1",
            POSSIBLE,
            PROBABLE,
        )
        by_peak = {a["sample_peak_id"]: a for a in assignments}
        child = by_peak["pB"]
        assert child["role"] == ROLE_ISO_CHILD
        assert child["isotope_label"] == "13C"
        assert (
            child["owner_peak_assignment_id"]
            == by_peak["pA"]["peak_assignment_id"]
        )

    def test_rows_without_observed_peak_are_skipped(self):
        assignments = untargeted_matches_to_peak_assignments(
            self._matches_df(),
            {100.1: ("pA", 5000.0)},  # pB's m/z missing from the lookup
            "sample1",
            "run1",
            POSSIBLE,
            PROBABLE,
        )
        assert [a["sample_peak_id"] for a in assignments] == ["pA"]

    def test_formula_formatter_is_applied(self):
        assignments = untargeted_matches_to_peak_assignments(
            self._matches_df(),
            self._peak_lookup(),
            "sample1",
            "run1",
            POSSIBLE,
            PROBABLE,
            formula_formatter=lambda formula: f"fmt({formula})",
        )
        by_peak = {a["sample_peak_id"]: a for a in assignments}
        assert by_peak["pA"]["assigned_formula"] == "fmt(C5H10O2)"
        assert by_peak["pA"]["alternatives"][0]["assigned_formula"] == (
            "fmt(C4H8N2O)"
        )

    def test_nan_mz_error_falls_back_to_composition_error(self):
        # A NaN mz_error_ppm (present column, no isotope-envelope error for this
        # row) must fall back to composition_error_ppm, not collapse the score.
        matches_df = pd.DataFrame(
            [
                {
                    "mz": 100.1,
                    "formula": "C5H10O2",
                    "ion": "C5H11O2+",
                    "isotope_label": "M0",
                    "ionization_mechanism": "+H+",
                    "mz_error_ppm": float("nan"),
                    "composition_error_ppm": 2.0,
                    "intensity_error": 0.1,
                    "other_candidates": "",
                }
            ]
        )
        assignments = untargeted_matches_to_peak_assignments(
            matches_df,
            {100.1: ("pA", 5000.0)},
            "sample1",
            "run1",
            POSSIBLE,
            PROBABLE,
            mechanism_id_by_notation={"+H+": "mech1"},
        )
        assert len(assignments) == 1
        # score = (1 - 0.1) * (1 - 2.0/100), not 0 from a collapsed mz term.
        assert assignments[0]["match_score"] == pytest.approx(0.9 * 0.98)
        assert assignments[0]["tier"] == TIER_IDENTIFIED

    def test_ionization_placeholder_formula_is_skipped(self):
        # The finder emits "()" for reagent/ionization peaks; it is not a
        # molecular formula and must not be persisted as one.
        matches_df = pd.DataFrame(
            [
                {
                    "mz": 19.018,
                    "formula": "()",
                    "ion": "H3O+",
                    "isotope_label": "M0",
                    "ionization_mechanism": "+H+",
                    "mz_error_ppm": 1.0,
                    "intensity_error": 0.0,
                    "other_candidates": "",
                }
            ]
        )
        assignments = untargeted_matches_to_peak_assignments(
            matches_df,
            {19.018: ("pR", 1000.0)},
            "sample1",
            "run1",
            POSSIBLE,
            PROBABLE,
        )
        assert assignments == []


class TestBuildUnassigned:
    def test_every_leftover_peak_gets_a_placeholder_row(self):
        peaks_df = pd.DataFrame(
            {
                "sample_peak_id": ["p9", "p10"],
                "mz": [55.05, 56.06],
                "intensity": [12.0, 0.0],
            }
        )
        rows = build_unassigned_assignments(peaks_df, "sample1", "run1")

        assert len(rows) == 2
        for row in rows:
            assert row["role"] == ROLE_UNASSIGNED
            assert row["tier"] == TIER_UNASSIGNED
            assert row["source"] is None
            assert row["assigned_formula"] is None
            assert row["peak_assignment_run_id"] == "run1"
            assert row["sample_item_id"] == "sample1"
        assert rows[0]["sample_peak_id"] == "p9"
        assert rows[0]["sample_peak_mz"] == pytest.approx(55.05)
