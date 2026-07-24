"""
Known-answer tests for the match aggregation pipeline
(``api/controllers/match/lib/match_aggregate.py``).

Aggregation climbs isotope -> ion -> compound -> collection/sample. The rules
under test:

- Ion score = sum of isotope scores weighted by relative abundance.
- Ion match category from probable/possible thresholds (defaults, explicit
  params, or per-ion stored filter params).
- Compound/collection/sample aggregation keeps the most alarming member's
  score + category (sorted by category, then score) and sums intensities.
- Sample aggregation prioritizes alarming collection types over score.
- ``compile_samples_df`` merges aggregates into the sample listing, flags
  ``matched`` and zero-fills samples with no matches.
"""

import pandas as pd
import pytest

from mascope_backend.api.controllers.match.lib.match_aggregate import (
    MATCH_ISOTOPE_VALUE_COLUMNS,
    aggregate_match_collections,
    aggregate_match_compounds,
    aggregate_match_compounds_light,
    aggregate_match_ions,
    aggregate_match_ions_light,
    aggregate_match_samples,
    compile_samples_df,
    reconstruct_full_isotope_frame,
    set_alarm_mode,
    set_ions_match_category,
)
from mascope_match.params import BaseMatchParams


def make_match_params(probable: float, possible: float) -> BaseMatchParams:
    """BaseMatchParams with only the threshold fields relevant to these tests."""
    return BaseMatchParams(
        probable_match_threshold=probable,
        possible_match_threshold=possible,
        mz_tolerance=5,
        isotope_ratio_tolerance=0.2,
        peak_min_intensity=0,
        isotope_abundance_threshold=1e-5,
    )


class TestSetIonsMatchCategory:
    @pytest.mark.asyncio
    async def test_default_thresholds(self):
        # Defaults: probable 0.8, possible 0.7.
        df = pd.DataFrame(
            {
                "match_score": [0.85, 0.75, 0.65],
                "instrument": ["orbi"] * 3,
                "filter_params": [None] * 3,
            }
        )

        result = await set_ions_match_category(df)

        assert result["match_category"].tolist() == [2, 1, 0]

    @pytest.mark.asyncio
    async def test_explicit_params_override_defaults(self):
        df = pd.DataFrame(
            {
                "match_score": [0.95, 0.7, 0.5],
                "instrument": ["orbi"] * 3,
                "filter_params": [None] * 3,
            }
        )

        result = await set_ions_match_category(
            df, make_match_params(probable=0.9, possible=0.6)
        )

        assert result["match_category"].tolist() == [2, 1, 0]

    @pytest.mark.asyncio
    async def test_ion_specific_filter_params_used_when_no_explicit_params(self):
        # Stored per-ion thresholds (keyed by instrument) reclassify a score
        # that would be 0 under the defaults.
        ion_filters = {
            "orbi": {"probable_match_threshold": 0.5, "possible_match_threshold": 0.3}
        }
        df = pd.DataFrame(
            {
                "match_score": [0.6, 0.4, 0.2],
                "instrument": ["orbi"] * 3,
                "filter_params": [ion_filters] * 3,
            }
        )

        result = await set_ions_match_category(df)

        assert result["match_category"].tolist() == [2, 1, 0]

    @pytest.mark.asyncio
    async def test_explicit_params_beat_ion_specific_filters(self):
        ion_filters = {
            "orbi": {"probable_match_threshold": 0.1, "possible_match_threshold": 0.05}
        }
        df = pd.DataFrame(
            {
                "match_score": [0.6],
                "instrument": ["orbi"],
                "filter_params": [ion_filters],
            }
        )

        result = await set_ions_match_category(
            df, make_match_params(probable=0.9, possible=0.7)
        )

        assert result["match_category"].tolist() == [0]


class TestAggregateMatchIonsLight:
    def test_weighted_score_and_summed_intensity(self):
        # Ion score = sum(isotope score * relative abundance); intensities sum.
        df = pd.DataFrame(
            {
                "target_ion_id": ["ion_1", "ion_1", "ion_2"],
                "match_score": [1.0, 0.5, 0.8],
                "relative_abundance": [1.0, 0.5, 1.0],
                "sample_peak_intensity": [100.0, 20.0, 40.0],
            }
        )

        result = aggregate_match_ions_light(df).set_index("target_ion_id")

        assert result.loc["ion_1", "match_score"] == pytest.approx(
            1.0 * 1.0 + 0.5 * 0.5
        )
        assert result.loc["ion_1", "sample_peak_intensity_sum"] == 120.0
        assert result.loc["ion_2", "match_score"] == pytest.approx(0.8)
        assert result.loc["ion_2", "sample_peak_intensity_sum"] == 40.0


class TestAggregateMatchCompoundsLight:
    def test_max_score_and_summed_intensity(self):
        df = pd.DataFrame(
            {
                "target_compound_id": ["comp_1", "comp_1", "comp_2"],
                "match_score": [0.9, 0.4, 0.7],
                "sample_peak_intensity_sum": [10.0, 5.0, 3.0],
            }
        )

        result = aggregate_match_compounds_light(df).set_index("target_compound_id")

        assert result.loc["comp_1", "match_score"] == 0.9
        assert result.loc["comp_1", "sample_peak_intensity_sum"] == 15.0
        assert result.loc["comp_2", "match_score"] == 0.7


class TestAggregateMatchCollections:
    @pytest.mark.asyncio
    async def test_most_alarming_compound_wins_and_intensity_sums(self):
        # Category outranks raw score: the category-2 compound's score (0.85)
        # must be kept even though a category-1 compound scores higher (0.99).
        df = pd.DataFrame(
            {
                "sample_item_id": ["s1"] * 2,
                "target_collection_id": ["coll_1"] * 2,
                "target_collection_name": ["Targets"] * 2,
                "target_collection_description": [""] * 2,
                "target_collection_type": ["TARGETS"] * 2,
                "match_score": [0.85, 0.99],
                "match_category": [2, 1],
                "sample_peak_intensity_sum": [10.0, 5.0],
            }
        )

        result = await aggregate_match_collections(df)

        assert len(result) == 1
        row = result.iloc[0]
        assert row["match_score"] == 0.85
        assert row["match_category"] == 2
        assert row["sample_peak_intensity_sum"] == 15.0


class TestAggregateMatchSamples:
    @pytest.mark.asyncio
    async def test_alarming_collection_type_outranks_score_and_category(self):
        # The TARGETS collection is alarming; its compound must define the
        # sample's score/category even though the calibration compound has a
        # higher category and score.
        df = pd.DataFrame(
            {
                "filename": ["f.raw"] * 2,
                "sample_item_id": ["s1"] * 2,
                "sample_item_name": ["sample 1"] * 2,
                "target_compound_id": ["comp_target", "comp_cal"],
                "target_collection_type": ["TARGETS", "CALIBRATION"],
                "match_score": [0.75, 0.95],
                "match_category": [1, 2],
                "sample_peak_intensity_sum": [10.0, 30.0],
            }
        )

        result = await aggregate_match_samples(df)

        assert len(result) == 1
        row = result.iloc[0]
        assert row["match_score"] == 0.75
        assert row["match_category"] == 1
        assert row["sample_peak_intensity_sum"] == 40.0

    @pytest.mark.asyncio
    async def test_duplicate_compound_across_collections_counted_once(self):
        # The same compound matched via two collections must not double its
        # intensity contribution to the sample total.
        df = pd.DataFrame(
            {
                "filename": ["f.raw"] * 2,
                "sample_item_id": ["s1"] * 2,
                "sample_item_name": ["sample 1"] * 2,
                "target_compound_id": ["comp_1", "comp_1"],
                "target_collection_type": ["TARGETS", "DIAGNOSTIC"],
                "match_score": [0.9, 0.9],
                "match_category": [2, 2],
                "sample_peak_intensity_sum": [10.0, 10.0],
            }
        )

        result = await aggregate_match_samples(df)

        assert len(result) == 1
        assert result.iloc[0]["sample_peak_intensity_sum"] == 10.0


class TestStoredFrameNaturalKeys:
    """
    The persisted ion/compound frames must be unique on their natural keys
    even when a compound is shared by several collections of the batch - the
    database enforces this with unique constraints
    (uq_match_ion_sample_item_target_ion etc.), so the per-collection
    duplication of the working frames must never leak into the stored frames.
    """

    @staticmethod
    def make_isotope_frame() -> pd.DataFrame:
        # One compound/ion with two isotopes, reached through TWO collections
        # of the same sample: 4 working rows, but one logical ion.
        rows = []
        for collection in ("coll_a", "coll_b"):
            for isotope, score, abundance, intensity in (
                ("iso_1", 0.9, 1.0, 100.0),
                ("iso_2", 0.5, 0.1, 50.0),
            ):
                rows.append(
                    {
                        "sample_item_id": "s1",
                        "sample_item_name": "sample 1",
                        "sample_item_type": "ANALYSIS",
                        "filename": "f.raw",
                        "instrument": "orbi",
                        "target_ion_id": "ion_1",
                        "target_ion_formula": "C6H13O6+",
                        "ionization_mechanism": "[M+H]+",
                        "target_compound_id": "comp_1",
                        "target_compound_formula": "C6H12O6",
                        "target_compound_name": "Glucose",
                        "target_collection_id": collection,
                        "target_collection_name": collection,
                        "target_collection_description": "",
                        "target_collection_type": "TARGETS",
                        "target_isotope_id": isotope,
                        "match_score": score,
                        "relative_abundance": abundance,
                        "sample_peak_intensity": intensity,
                        "filter_params": None,
                    }
                )
        return pd.DataFrame(rows)

    @pytest.mark.asyncio
    async def test_shared_compound_yields_unique_stored_ion_rows(self):
        ions_data_df, ions_df = await aggregate_match_ions(self.make_isotope_frame())

        # Working frame keeps per-collection context; stored frame is unique
        # on (sample_item_id, target_ion_id) with the per-collection values
        # identical, not doubled.
        assert len(ions_data_df) == 2
        assert not ions_df.duplicated(["sample_item_id", "target_ion_id"]).any()
        assert len(ions_df) == 1
        assert ions_df.iloc[0]["match_score"] == pytest.approx(0.9 * 1.0 + 0.5 * 0.1)
        assert ions_df.iloc[0]["sample_peak_intensity_sum"] == pytest.approx(150.0)

    @pytest.mark.asyncio
    async def test_shared_compound_yields_unique_stored_compound_rows(self):
        ions_data_df, _ = await aggregate_match_ions(self.make_isotope_frame())
        compounds_data_df, compounds_df = await aggregate_match_compounds(ions_data_df)

        assert len(compounds_data_df) == 2  # one per collection
        assert not compounds_df.duplicated(
            ["sample_item_id", "target_compound_id"]
        ).any()
        assert len(compounds_df) == 1
        # Intensity summed within one collection's ions - not doubled across
        # the collections.
        assert compounds_df.iloc[0]["sample_peak_intensity_sum"] == pytest.approx(150.0)


class TestSetAlarmMode:
    @pytest.mark.asyncio
    async def test_alarm_mode_follows_collection_type(self):
        df = pd.DataFrame(
            {"target_collection_type": ["TARGETS", "CALIBRATION", "DIAGNOSTIC"]}
        )

        result = await set_alarm_mode(df)

        assert result["alarm_mode"].tolist() == [True, False, False]


class TestCompileSamplesDf:
    @pytest.mark.asyncio
    async def test_merges_matches_and_zero_fills_unmatched(self):
        samples_df = pd.DataFrame(
            {
                "sample_item_id": ["s1", "s2"],
                "tic": [1000.0, None],
            }
        )
        match_samples_df = pd.DataFrame(
            {
                "sample_item_id": ["s1"],
                "match_score": [0.9],
                "match_category": [2],
                "sample_peak_intensity_sum": [123.0],
            }
        )

        result = await compile_samples_df(samples_df, match_samples_df)

        s1 = result[result["sample_item_id"] == "s1"].iloc[0]
        s2 = result[result["sample_item_id"] == "s2"].iloc[0]
        assert s1["matched"] == 1
        assert s1["match_score"] == 0.9
        assert s2["matched"] == 0
        assert s2["match_score"] == 0.0
        assert s2["match_category"] == 0.0
        assert s2["tic"] == 0.0


# Orbitrap: resolution HIGH, default isotope_abundance_threshold 1e-5.
def _orbi_samples() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "sample_item_id": ["s1"],
            "instrument": ["orbi"],
            "filename": ["orbi_2024.01.01_10h00m00s.h5"],
        }
    )


def _orbi_targets() -> pd.DataFrame:
    # iA: main, high abundance; iB: minor but above threshold; iC: below the
    # 1e-5 threshold; iD: wrong (LOW) resolution for an Orbitrap sample.
    return pd.DataFrame(
        {
            "target_isotope_id": ["iA", "iB", "iC", "iD"],
            "target_ion_id": ["ion1", "ion1", "ion1", "ion1"],
            "relative_abundance": [1.0, 0.1, 1e-6, 0.5],
            "resolution": ["HIGH", "HIGH", "HIGH", "LOW"],
            "filter_params": [None, None, None, None],
            "mz": [100.0, 101.0, 102.0, 103.0],
        }
    )


def _empty_stored() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["sample_item_id", "target_isotope_id"] + MATCH_ISOTOPE_VALUE_COLUMNS
    )


class TestReconstructFullIsotopeFrame:
    """Unmatched isotopes are no longer stored; reconstruct_full_isotope_frame
    rebuilds them from the target isotopes so the isotope table and aggregates
    stay identical to when they were persisted."""

    def test_reconstructs_unmatched_in_population_and_preserves_matched(self):
        stored = pd.DataFrame(
            [
                {
                    "sample_item_id": "s1",
                    "target_isotope_id": "iA",
                    "match_mz_error": 0.5,
                    "match_abundance_error": 0.05,
                    "sample_peak_intensity": 1000.0,
                    "sample_peak_intensity_relative": 1.0,
                    "sample_peak_mz": 100.0001,
                    "sample_peak_tof": 12.3,
                    "match_score": 0.97,
                }
            ]
        )

        result = reconstruct_full_isotope_frame(
            stored, _orbi_samples(), _orbi_targets()
        ).set_index("target_isotope_id")

        # Matched isotope preserved untouched.
        assert result.loc["iA", "match_score"] == 0.97
        assert result.loc["iA", "sample_peak_intensity"] == 1000.0

        # Minor-but-above-threshold isotope reconstructed with unmatched defaults.
        assert "iB" in result.index
        assert result.loc["iB", "match_score"] == 0.0
        assert result.loc["iB", "sample_peak_intensity"] == 0.0
        assert result.loc["iB", "sample_peak_intensity_relative"] == 0.0
        assert result.loc["iB", "match_abundance_error"] == 1.0
        assert result.loc["iB", "match_mz_error"] == 0.0
        assert result.loc["iB", "sample_peak_tof"] == -1.0
        assert result.loc["iB", "sample_peak_mz"] == 101.0  # target m/z

        # Below-threshold and wrong-resolution isotopes are not reconstructed.
        assert "iC" not in result.index
        assert "iD" not in result.index

    def test_matched_row_with_zero_score_is_preserved(self):
        # A real matched peak can score exactly 0; it must keep its peak data and
        # not be mistaken for a reconstructed unmatched row.
        stored = pd.DataFrame(
            [
                {
                    "sample_item_id": "s1",
                    "target_isotope_id": "iA",
                    "match_mz_error": 9.0,
                    "match_abundance_error": 1.0,
                    "sample_peak_intensity": 500.0,
                    "sample_peak_intensity_relative": 0.3,
                    "sample_peak_mz": 100.02,
                    "sample_peak_tof": 5.0,
                    "match_score": 0.0,
                }
            ]
        )
        targets = _orbi_targets().iloc[[0]].copy()  # only iA

        result = reconstruct_full_isotope_frame(
            stored, _orbi_samples(), targets
        ).set_index("target_isotope_id")

        assert result.loc["iA", "sample_peak_intensity"] == 500.0
        assert result.loc["iA", "sample_peak_mz"] == 100.02

    def test_per_ion_threshold_override_excludes_isotope(self):
        targets = _orbi_targets()
        # Raise the ion's threshold above iB's abundance -> iB drops out.
        targets["filter_params"] = [
            {"orbi": {"isotope_abundance_threshold": 0.2}}
        ] * len(targets)

        result = reconstruct_full_isotope_frame(
            _empty_stored(), _orbi_samples(), targets
        )
        ids = set(result["target_isotope_id"])

        assert "iA" in ids  # 1.0 >= 0.2
        assert "iB" not in ids  # 0.1 < 0.2
        assert "iC" not in ids
        assert "iD" not in ids

    def test_fully_unmatched_sample_reconstructs_whole_population(self):
        # With no stored rows, every above-threshold, right-resolution isotope
        # comes back as unmatched (score 0) so the ion still aggregates.
        result = reconstruct_full_isotope_frame(
            _empty_stored(), _orbi_samples(), _orbi_targets()
        )

        assert set(result["target_isotope_id"]) == {"iA", "iB"}
        assert (result["match_score"] == 0.0).all()

    def test_aggregate_score_matches_matched_only(self):
        # Reconstructed unmatched rows (score 0, intensity 0) must not change the
        # ion aggregate vs. aggregating the matched rows alone.
        stored = pd.DataFrame(
            [
                {
                    "sample_item_id": "s1",
                    "target_isotope_id": "iA",
                    "match_mz_error": 0.5,
                    "match_abundance_error": 0.05,
                    "sample_peak_intensity": 1000.0,
                    "sample_peak_intensity_relative": 1.0,
                    "sample_peak_mz": 100.0001,
                    "sample_peak_tof": 12.3,
                    "match_score": 0.9,
                }
            ]
        )
        targets = _orbi_targets()

        full = reconstruct_full_isotope_frame(stored, _orbi_samples(), targets)
        full = full.merge(
            targets[["target_isotope_id", "target_ion_id", "relative_abundance"]],
            on="target_isotope_id",
        )
        matched_only = stored.merge(
            targets[["target_isotope_id", "target_ion_id", "relative_abundance"]],
            on="target_isotope_id",
        )

        full_ion = aggregate_match_ions_light(full).set_index("target_ion_id")
        matched_ion = aggregate_match_ions_light(matched_only).set_index(
            "target_ion_id"
        )

        assert full_ion.loc["ion1", "match_score"] == pytest.approx(
            matched_ion.loc["ion1", "match_score"]
        )
        assert full_ion.loc["ion1", "sample_peak_intensity_sum"] == pytest.approx(
            matched_ion.loc["ion1", "sample_peak_intensity_sum"]
        )
