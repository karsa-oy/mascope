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
    aggregate_match_collections,
    aggregate_match_compounds_light,
    aggregate_match_ions_light,
    aggregate_match_samples,
    compile_samples_df,
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
