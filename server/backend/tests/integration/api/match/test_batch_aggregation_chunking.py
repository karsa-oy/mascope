"""
Integration tests for chunked batch aggregation
(``api/controllers/match/aggregate/match_aggregate_controller.py``).

Batch-scope ``aggregate_and_create_matches`` processes samples in bounded
chunks (BATCH_AGGREGATION_CHUNK_SIZE) so the reconstructed isotope frame of a
large batch cannot exhaust process memory. The rules under test:

- Chunked aggregation covers every sample and produces the same persisted
  values as a single pass (every aggregate level is per-sample).
- MatchSample rows are cleared up front and restored chunk by chunk: they are
  the aggregation-completeness signal for match_compute_batch's skip probe,
  so a failure mid-aggregation must leave the probe reporting incomplete.
- Re-running the aggregation is consistent (same values, no duplicates).
"""

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
import pytest_asyncio
from sqlalchemy import select

import mascope_backend.api.controllers.match.aggregate.match_aggregate_controller as mac
from mascope_backend.api.controllers.match.match_controller import (
    _batch_aggregates_incomplete,
)
from mascope_backend.db import (
    Dataset,
    IonizationMechanism,
    IonizationMode,
    MatchIon,
    MatchIsotope,
    MatchSample,
    SampleBatch,
    SampleFile,
    SampleItem,
    TargetCollection,
    TargetCollectionInSampleBatch,
    TargetCompound,
    TargetCompoundInTargetCollection,
    TargetIon,
    TargetIsotope,
    Workspace,
)
from mascope_backend.db.id import gen_id
from mascope_backend.socket.notifications import UserNotification
from mascope_match.params import BaseMatchParams


_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
_NOW_NAIVE = datetime(2026, 1, 1)

MATCH_PARAMS = BaseMatchParams(
    probable_match_threshold=0.8,
    possible_match_threshold=0.7,
    mz_tolerance=5,
    isotope_ratio_tolerance=0.2,
    peak_min_intensity=0,
    isotope_abundance_threshold=1e-5,
)

SAMPLE_COUNT = 3


@pytest_asyncio.fixture
async def aggregation_chain(async_session_factory):
    """
    A batch of SAMPLE_COUNT samples sharing one target chain: one collection,
    one compound, two ions with two isotopes each (HIGH resolution).

    Every sample stores one scoring row for ion 1's main isotope
    (score 0.8, abundance weight 1.0) and one zero-score sentinel for ion 2 -
    so the expected aggregated ion scores are 0.8 and 0.0 per sample.
    """
    ids = SimpleNamespace(
        workspace=gen_id(),
        dataset=gen_id(),
        batch=gen_id(),
        file=gen_id(),
        items=[gen_id() for _ in range(SAMPLE_COUNT)],
        mechanism=gen_id(),
        mode=gen_id(),
        collection=gen_id(),
        compound=gen_id(),
        ion1=gen_id(),
        ion2=gen_id(),
        iso1a=gen_id(),
        iso1b=gen_id(),
        iso2a=gen_id(),
        iso2b=gen_id(),
    )
    async with async_session_factory() as session:
        session.add(
            Workspace(
                workspace_id=ids.workspace,
                workspace_name=f"Agg WS {ids.workspace}",
                workspace_description="Chunked aggregation test workspace",
                workspace_status="active",
                workspace_utc_created=_NOW,
                workspace_utc_modified=_NOW,
            )
        )
        session.add(
            Dataset(
                dataset_id=ids.dataset,
                workspace_id=ids.workspace,
                dataset_name=f"Agg DS {ids.dataset}",
                dataset_description="Chunked aggregation test dataset",
                dataset_type="ANALYSIS",
                dataset_utc_created=_NOW,
            )
        )
        session.add(
            SampleBatch(
                sample_batch_id=ids.batch,
                dataset_id=ids.dataset,
                sample_batch_name="Chunked Aggregation Batch",
                sample_batch_utc_created=_NOW,
            )
        )
        session.add(
            SampleFile(
                sample_file_id=ids.file,
                filename=f"test-orbion_{ids.file}.raw",
                instrument="test-orbion",
                datetime=_NOW_NAIVE,
                datetime_utc=_NOW,
                length=60.0,
                range={"min": 0, "max": 500},
                polarity="+",
            )
        )
        session.add(
            IonizationMechanism(
                ionization_mechanism_id=ids.mechanism,
                ionization_mechanism_polarity="+",
                ionization_mechanism=f"[M+H]+ {ids.mechanism}",
            )
        )
        session.add(
            IonizationMode(
                ionization_mode_id=ids.mode,
                ionization_mode_name="Chunked Aggregation Mode",
                ionization_mode_polarity="+",
                ionization_mechanism_ids=[ids.mechanism],
            )
        )
        for index, item_id in enumerate(ids.items):
            session.add(
                SampleItem(
                    sample_item_id=item_id,
                    sample_batch_id=ids.batch,
                    sample_file_id=ids.file,
                    ionization_mode_id=ids.mode,
                    sample_item_name=f"Agg Item {index + 1}",
                    sample_item_type="ANALYSIS",
                    sample_item_attributes={},
                    polarity="+",
                    tic=1000.0,
                    t0=0.0,
                    t1=60.0,
                    sample_item_utc_created=_NOW,
                )
            )
        session.add(
            TargetCollection(
                target_collection_id=ids.collection,
                target_collection_name=f"Agg Collection {ids.collection}",
                # NULL description would NaN a groupby key and silently drop
                # every row from the aggregation (pandas groupby dropna)
                target_collection_description="",
                target_collection_type="TARGETS",
                workspace_id=ids.workspace,
            )
        )
        session.add(
            TargetCollectionInSampleBatch(
                target_collection_id=ids.collection,
                sample_batch_id=ids.batch,
            )
        )
        session.add(
            TargetCompound(
                target_compound_id=ids.compound,
                target_compound_name=f"Agg Compound {ids.compound}",
                target_compound_formula="C6H12O6",
            )
        )
        session.add(
            TargetCompoundInTargetCollection(
                target_compound_id=ids.compound,
                target_collection_id=ids.collection,
            )
        )
        for ion_id in (ids.ion1, ids.ion2):
            session.add(
                TargetIon(
                    target_ion_id=ion_id,
                    target_compound_id=ids.compound,
                    ionization_mechanism_id=ids.mechanism,
                    target_ion_formula="C6H13O6+",
                )
            )
        isotopes = [
            (ids.iso1a, ids.ion1, 181.07, 1.0),
            (ids.iso1b, ids.ion1, 182.07, 0.1),
            (ids.iso2a, ids.ion2, 203.05, 1.0),
            (ids.iso2b, ids.ion2, 204.05, 0.06),
        ]
        for isotope_id, ion_id, mz, abundance in isotopes:
            session.add(
                TargetIsotope(
                    target_isotope_id=isotope_id,
                    target_ion_id=ion_id,
                    target_isotope_formula="C6H13O6+",
                    mz=mz,
                    relative_abundance=abundance,
                    resolution="HIGH",
                )
            )
        # Stored match isotopes: one scoring row (ion 1 main isotope) and one
        # zero-score sentinel (ion 2 main isotope) per sample.
        for item_id in ids.items:
            for isotope_id, score, intensity in (
                (ids.iso1a, 0.8, 1000.0),
                (ids.iso2a, 0.0, 0.0),
            ):
                session.add(
                    MatchIsotope(
                        match_isotope_id=gen_id(32),
                        target_isotope_id=isotope_id,
                        sample_item_id=item_id,
                        sample_peak_id=gen_id(20) if score > 0 else "",
                        sample_peak_mz=0.0,
                        sample_peak_intensity=intensity,
                        sample_peak_intensity_relative=0.0,
                        sample_peak_tof=0.0,
                        match_abundance_error=0.0,
                        match_mz_error=0.0,
                        match_score=score,
                        match_isotope_utc_created=_NOW,
                    )
                )
        await session.commit()
    return ids


async def fetch_level_rows(async_session_factory, model, sample_item_ids):
    """All rows of a match level for the given samples."""
    async with async_session_factory() as session:
        return (
            (
                await session.execute(
                    select(model).where(model.sample_item_id.in_(sample_item_ids))
                )
            )
            .scalars()
            .all()
        )


class TestChunkedBatchAggregation:
    @pytest.mark.asyncio
    async def test_chunked_aggregation_covers_all_samples(
        self, aggregation_chain, async_session_factory, monkeypatch
    ):
        # One sample per chunk: SAMPLE_COUNT independent aggregate+create
        # passes must together cover the whole batch.
        monkeypatch.setattr(mac, "BATCH_AGGREGATION_CHUNK_SIZE", 1)

        # Capture the per-chunk progress reports (UI progress after the
        # per-sample compute bar completes)
        progress_calls = []

        async def record_progress(notification, increment=None):
            progress_calls.append(
                (
                    notification.data.get("_item_index"),
                    notification.data.get("_total_samples"),
                )
            )

        monkeypatch.setattr(mac, "send_progress_user_notification", record_progress)
        notification = UserNotification(
            process_id="stress-test",
            type="match_aggregate_batch",
            status="pending",
            message="Aggregating",
            data={},
        )

        result = await mac.aggregate_and_create_matches(
            sample_batch_id=aggregation_chain.batch,
            match_params=MATCH_PARAMS,
            notification=notification,
        )

        assert result["status"] == "success"
        assert progress_calls == [(i, SAMPLE_COUNT) for i in range(SAMPLE_COUNT)]
        assert set(result["data"]["affected_sample_item_ids"]) == set(
            aggregation_chain.items
        )

        ions = await fetch_level_rows(
            async_session_factory, MatchIon, aggregation_chain.items
        )
        assert len(ions) == 2 * SAMPLE_COUNT
        by_key = {(ion.sample_item_id, ion.target_ion_id): ion for ion in ions}
        for item_id in aggregation_chain.items:
            # Ion score = sum(isotope score * relative abundance); the
            # reconstructed zero rows and the sentinel contribute 0.
            assert by_key[(item_id, aggregation_chain.ion1)].match_score == (
                pytest.approx(0.8)
            )
            assert by_key[(item_id, aggregation_chain.ion2)].match_score == 0.0

        samples = await fetch_level_rows(
            async_session_factory, MatchSample, aggregation_chain.items
        )
        assert len(samples) == SAMPLE_COUNT
        assert not await _batch_aggregates_incomplete(aggregation_chain.batch)

    @pytest.mark.asyncio
    async def test_rerun_is_consistent(
        self, aggregation_chain, async_session_factory, monkeypatch
    ):
        monkeypatch.setattr(mac, "BATCH_AGGREGATION_CHUNK_SIZE", 2)

        for _ in range(2):
            result = await mac.aggregate_and_create_matches(
                sample_batch_id=aggregation_chain.batch, match_params=MATCH_PARAMS
            )
            assert result["status"] in ("success", "partial")

        ions = await fetch_level_rows(
            async_session_factory, MatchIon, aggregation_chain.items
        )
        # Still unique per (sample, ion) - no duplicates from the second run
        assert len(ions) == 2 * SAMPLE_COUNT
        samples = await fetch_level_rows(
            async_session_factory, MatchSample, aggregation_chain.items
        )
        assert len(samples) == SAMPLE_COUNT

    @pytest.mark.asyncio
    async def test_failed_chunk_leaves_completeness_probe_incomplete(
        self, aggregation_chain, async_session_factory, monkeypatch
    ):
        # First aggregate fully so every sample has a MatchSample row.
        await mac.aggregate_and_create_matches(
            sample_batch_id=aggregation_chain.batch, match_params=MATCH_PARAMS
        )
        assert not await _batch_aggregates_incomplete(aggregation_chain.batch)

        # Then re-aggregate with a failure injected into the second chunk:
        # the up-front MatchSample clearing must leave the batch probing as
        # incomplete, so the next refresh re-aggregates instead of skipping.
        monkeypatch.setattr(mac, "BATCH_AGGREGATION_CHUNK_SIZE", 1)
        calls = {"count": 0}
        original_create_match_ions = mac.create_match_ions

        async def failing_create_match_ions(model_data):
            calls["count"] += 1
            if calls["count"] >= 2:
                raise RuntimeError("injected chunk failure")
            return await original_create_match_ions(model_data)

        monkeypatch.setattr(mac, "create_match_ions", failing_create_match_ions)

        # The injected error surfaces wrapped by the api_controller layer;
        # the exact exception type/message is not the contract here.
        with pytest.raises(Exception):  # noqa: B017
            await mac.aggregate_and_create_matches(
                sample_batch_id=aggregation_chain.batch, match_params=MATCH_PARAMS
            )

        assert await _batch_aggregates_incomplete(aggregation_chain.batch)
