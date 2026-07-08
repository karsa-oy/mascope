"""
Peak-centric assignment service.

Orchestrates the two-stage assignment engine over a sample and provides the
read model ("every peak in sample X with its formula and confidence"):

- Stage A (database-first): every peak is matched against the known target
  isotopologue library by reusing the targeted matcher, then the result is
  inverted from target-anchored to peak-anchored rows (source='database').
- Stage B (untargeted): peaks Stage A left unexplained are run through the
  mascope_tools composition finder (source='untargeted').
- Remaining peaks are persisted as 'unassigned' so each run is a complete,
  queryable ledger with a single owner per peak.
"""

import asyncio
from datetime import datetime as dt
from datetime import timezone

import pandas as pd
from sqlalchemy import insert, select, update

from mascope_backend.api.controllers.samples.lib.samples_fetch import fetch_sample
from mascope_backend.api.controllers.samples.lib.samples_peaks import extract_peaks
from mascope_backend.api.lib.api_features import (
    api_controller,
    api_controller_background_task,
)
from mascope_backend.api.lib.exceptions.api_exceptions import (
    NotFoundException,
    raise_api_warning,
)
from mascope_backend.api.new.cheminfo.utils import (
    to_custom_element_format,
    to_explicit_isotope_format,
)
from mascope_backend.api.new.ionization.modes.util import (
    fetch_sample_ionization_mechanism_ids,
)
from mascope_backend.api.new.match.params import default_match_params
from mascope_backend.api.new.match.params.lib import (
    apply_match_params,
    isotope_abundance_threshold_expr,
)
from mascope_backend.api.new.peak_assignments.calibration_store import load_calibration
from mascope_backend.api.new.peak_assignments.config import (
    PEAK_ASSIGNMENT_ENGINE_VERSION,
    PeakAssignmentConfig,
)
from mascope_backend.api.new.peak_assignments.engine import (
    build_unassigned_assignments,
    invert_matches_to_peak_assignments,
    score_ions_by_fit,
    untargeted_matches_to_peak_assignments,
)
from mascope_backend.db import (
    IonizationMechanism,
    PeakAssignment,
    PeakAssignmentRun,
    Sample,
    TargetCollectionInSampleBatch,
    TargetCompound,
    TargetCompoundInTargetCollection,
    TargetIon,
    TargetIsotope,
    async_session,
)
from mascope_backend.db.id import gen_id
from mascope_backend.runtime import runtime
from mascope_backend.socket.notifications import (
    UserNotification,
    send_progress_user_notification,
)
from mascope_file.name import get_instrument_type
from mascope_match import compute_match_isotopes
from mascope_tools.composition import CompositionSearchConfig
from mascope_tools.composition.finder import assign_compositions
from mascope_tools.composition.heuristic_filter import SCORE_VERSION


# -------------------------------------------------------------------
# Read model
# -------------------------------------------------------------------


@api_controller()
async def get_peak_assignment_runs(sample_item_id: str) -> dict:
    """
    Retrieve all peak assignment runs for a sample, newest first.

    :param sample_item_id: Unique identifier of the sample item
    :return: Dictionary with status, message, results count, and run records
    """
    sample = await fetch_sample(sample_item_id)

    async with async_session() as session:
        runs = (
            (
                await session.execute(
                    select(PeakAssignmentRun)
                    .where(PeakAssignmentRun.sample_item_id == sample_item_id)
                    .order_by(PeakAssignmentRun.peak_assignment_run_utc_created.desc())
                )
            )
            .scalars()
            .all()
        )

    data = [run.to_dict() for run in runs]
    return {
        "status": "success",
        "message": (
            f"Retrieved {len(data)} peak assignment run"
            f"{'s' if len(data) != 1 else ''} "
            f"for sample '{sample.sample_item_name}'"
        ),
        "results": len(data),
        "data": data,
    }


@api_controller()
async def get_peak_assignments(
    sample_item_id: str,
    peak_assignment_run_id: str | None = None,
    tier: str | None = None,
    role: str | None = None,
    source: str | None = None,
) -> dict:
    """
    Retrieve peaks-with-assignments for a sample.

    Returns the assignments of the requested run, or of the latest completed
    run when no run id is given. Optional filters narrow by confidence tier,
    peak role, or assignment source.

    :param sample_item_id: Unique identifier of the sample item
    :param peak_assignment_run_id: Specific run to read; defaults to the
        latest completed run
    :param tier: Optional filter by confidence tier
    :param role: Optional filter by peak role
    :param source: Optional filter by assignment source (database/untargeted)
    :return: Dictionary with status, message, run record, and assignment rows
    """
    sample = await fetch_sample(sample_item_id)

    async with async_session() as session:
        if peak_assignment_run_id is not None:
            run = await session.get(PeakAssignmentRun, peak_assignment_run_id)
            if run is None or run.sample_item_id != sample_item_id:
                raise NotFoundException(
                    f"Peak assignment run '{peak_assignment_run_id}' not found "
                    f"for sample '{sample.sample_item_name}'"
                )
        else:
            run = (
                await session.execute(
                    select(PeakAssignmentRun)
                    .where(
                        PeakAssignmentRun.sample_item_id == sample_item_id,
                        PeakAssignmentRun.status == "completed",
                    )
                    .order_by(PeakAssignmentRun.peak_assignment_run_utc_created.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()

        if run is None:
            return {
                "status": "success",
                "message": (
                    f"No completed peak assignment runs exist for sample "
                    f"'{sample.sample_item_name}'"
                ),
                "results": 0,
                "run": None,
                "data": [],
            }

        query = (
            select(PeakAssignment)
            .where(PeakAssignment.peak_assignment_run_id == run.peak_assignment_run_id)
            .order_by(PeakAssignment.sample_peak_mz)
        )
        if tier:
            query = query.where(PeakAssignment.tier == tier)
        if role:
            query = query.where(PeakAssignment.role == role)
        if source:
            query = query.where(PeakAssignment.source == source)

        assignments = (await session.execute(query)).scalars().all()

    data = [assignment.to_dict() for assignment in assignments]
    return {
        "status": "success",
        "message": (
            f"Retrieved {len(data)} peak assignment"
            f"{'s' if len(data) != 1 else ''} "
            f"for sample '{sample.sample_item_name}'"
        ),
        "results": len(data),
        "run": run.to_dict(),
        "data": data,
    }


# -------------------------------------------------------------------
# Assignment engine orchestration
# -------------------------------------------------------------------


async def _fetch_known_target_isotopes(
    sample: Sample, isotope_abundance_threshold: float
) -> pd.DataFrame:
    """
    Fetch the full known-isotopologue set for a sample (Stage A input).

    Unlike fetch_sample_unmatched_target_isotopes this does not exclude
    already-matched isotopes - a peak assignment run always evaluates the
    whole library - and it carries the compound/ion metadata that ends up
    denormalized on PeakAssignment rows.

    :param sample: Sample model object
    :param isotope_abundance_threshold: Minimum relative abundance for a
        target isotope to participate
    :return: DataFrame of target isotopes with compound/ion metadata
    """
    async with async_session() as session:
        ionization_mechanism_ids = await fetch_sample_ionization_mechanism_ids(
            sample.sample_item_id
        )
        resolution_type = (
            "LOW" if get_instrument_type(sample.filename) == "tof" else "HIGH"
        )
        abundance_threshold = isotope_abundance_threshold_expr(
            TargetIon.filter_params,
            sample.instrument,
            isotope_abundance_threshold,
        )

        stmt = (
            select(
                TargetIsotope.target_isotope_id,
                TargetIsotope.target_ion_id,
                TargetIsotope.target_isotope_formula,
                TargetIsotope.mz,
                TargetIsotope.relative_abundance,
                TargetIsotope.resolution,
                TargetIon.target_ion_formula,
                TargetIon.ionization_mechanism_id,
                TargetCompound.target_compound_id,
                TargetCompound.target_compound_formula,
                IonizationMechanism.ionization_mechanism,
                IonizationMechanism.ionization_mechanism_polarity,
            )
            .distinct(TargetIsotope.target_isotope_id)
            .select_from(TargetIsotope)
            .join(TargetIon, TargetIon.target_ion_id == TargetIsotope.target_ion_id)
            .join(
                IonizationMechanism,
                IonizationMechanism.ionization_mechanism_id
                == TargetIon.ionization_mechanism_id,
            )
            .join(
                TargetCompound,
                TargetCompound.target_compound_id == TargetIon.target_compound_id,
            )
            .join(
                TargetCompoundInTargetCollection,
                TargetCompoundInTargetCollection.target_compound_id
                == TargetCompound.target_compound_id,
            )
            .join(
                TargetCollectionInSampleBatch,
                TargetCollectionInSampleBatch.target_collection_id
                == TargetCompoundInTargetCollection.target_collection_id,
            )
            .where(
                TargetCollectionInSampleBatch.sample_batch_id == sample.sample_batch_id,
                TargetIon.ionization_mechanism_id.in_(ionization_mechanism_ids),
                IonizationMechanism.ionization_mechanism_polarity == sample.polarity,
                TargetIsotope.resolution == resolution_type,
                TargetIsotope.relative_abundance >= abundance_threshold,
            )
        )
        if not (rows := (await session.execute(stmt)).all()):
            return pd.DataFrame()

    target_isotopes_df = pd.DataFrame([row._asdict() for row in rows])
    runtime.logger.info(
        f"Found {len(target_isotopes_df)} known target isotopes for sample "
        f"'{sample.sample_item_name}' (polarity: {sample.polarity})"
    )
    return target_isotopes_df


async def _fetch_untargeted_ionizations(
    sample: Sample,
) -> tuple[list[str], dict[str, str]]:
    """
    Resolve the sample's ionization mechanisms into the explicit-isotope
    notation used by the composition finder.

    :param sample: Sample model object
    :return: (explicit notation strings, notation -> mechanism id mapping)
    """
    mechanism_ids = await fetch_sample_ionization_mechanism_ids(sample.sample_item_id)
    async with async_session() as session:
        mechanisms = (
            (
                await session.execute(
                    select(IonizationMechanism).where(
                        IonizationMechanism.ionization_mechanism_id.in_(mechanism_ids),
                        IonizationMechanism.ionization_mechanism_polarity
                        == sample.polarity,
                    )
                )
            )
            .scalars()
            .all()
        )

    notations: list[str] = []
    mechanism_id_by_notation: dict[str, str] = {}
    for mechanism in mechanisms:
        notation, _ = to_explicit_isotope_format(mechanism.ionization_mechanism)
        notations.append(notation)
        mechanism_id_by_notation[notation] = mechanism.ionization_mechanism_id
    return notations, mechanism_id_by_notation


def _load_sample_peaks(sample: Sample) -> pd.DataFrame:
    """
    Load every observed peak of the sample with an averaged intensity.

    Uses peak heights for Orbitrap files and peak areas for TOF files,
    mirroring the targeted matcher.

    :param sample: Sample model object
    :return: DataFrame with sample_peak_id, mz, and intensity columns
    """
    peak_data = extract_peaks(sample.filename, sample.polarity, sample.t0, sample.t1)
    instrument_type = get_instrument_type(sample.filename)
    intensities = peak_data.heights if instrument_type == "orbi" else peak_data.areas
    peaks_df = pd.DataFrame(
        {
            "sample_peak_id": [str(peak_id) for peak_id in peak_data.peak_ids],
            "mz": peak_data.mz_values,
            "intensity": intensities if intensities is not None else 0.0,
        }
    )
    peaks_df["intensity"] = peaks_df["intensity"].fillna(0.0)
    return peaks_df


async def _create_run(
    sample_item_id: str, config: PeakAssignmentConfig
) -> PeakAssignmentRun:
    """Create and commit a PeakAssignmentRun row in 'running' state."""
    run = PeakAssignmentRun(
        peak_assignment_run_id=gen_id(16),
        sample_item_id=sample_item_id,
        engine_version=PEAK_ASSIGNMENT_ENGINE_VERSION,
        status="running",
        config=config.model_dump(),
        peak_assignment_run_utc_created=dt.now(timezone.utc),
    )
    async with async_session() as session:
        session.add(run)
        await session.commit()
    return run


async def _finalize_run(
    peak_assignment_run_id: str, status: str, error: str | None = None
) -> None:
    """Mark a run completed/failed with its completion timestamp."""
    async with async_session() as session:
        await session.execute(
            update(PeakAssignmentRun)
            .where(PeakAssignmentRun.peak_assignment_run_id == peak_assignment_run_id)
            .values(
                status=status,
                error=error,
                peak_assignment_run_utc_completed=dt.now(timezone.utc),
            )
        )
        await session.commit()


@api_controller_background_task(
    success_notification_rooms=["user_id"],
    error_notification_rooms=["user_id"],
    # Emit peak_assignment_reload to the sample's batch room on completion, so
    # the frontend run store refreshes via the useData events framework (mirrors
    # how rematch_sample emits match_reload). The room id resolves from the
    # returned _notification_data.sample_batch_id.
    success_reload=[("peak_assignment", "sample_batch_id")],
)
async def assign_sample_peaks(
    sample_item_id: str,
    config: PeakAssignmentConfig | None = None,
    independent_transaction: bool = False,
    user_id: int | None = None,
    process_id: str | None = None,
    parent_id: str | None = None,
) -> dict:
    """
    Run the two-stage peak assignment engine over a sample.

    Every observed peak of the sample gets exactly one PeakAssignment row in
    a new PeakAssignmentRun: Stage A assigns from the known target library,
    Stage B (optional) assigns the remainder via untargeted composition
    search, and leftover peaks are persisted as unassigned.

    :param sample_item_id: ID of the sample item to assign
    :param config: Optional run configuration; defaults are used when omitted
    :param independent_transaction: Flag for transaction handling
    :param user_id: Current user triggered operation (for user notifications)
    :param process_id: Process identifier for progress tracking
    :param parent_id: Parent process identifier
    :return: A dictionary with run summary and status message
    """
    sample = await fetch_sample(sample_item_id)
    config = config or PeakAssignmentConfig()

    if sample.instrument_function_id is None:
        # Blank samples carry no peaks; nothing to assign
        warning_message = (
            f"Sample '{sample.sample_item_name}' has no peaks. "
            "Peak assignment is skipped."
        )
        raise_api_warning(warning_message, {"sample_item_id": sample_item_id})
        return {
            "status": "skipped",
            "message": warning_message,
            "_notification_data": {
                "sample_batch_id": sample.sample_batch_id,
                "sample_item_id": sample_item_id,
            },
        }

    match_params = await default_match_params(sample_item_id)
    run = await _create_run(sample_item_id, config)
    runtime.logger.info(
        f"Starting peak assignment run '{run.peak_assignment_run_id}' "
        f"for sample '{sample.sample_item_name}'"
    )

    notification = UserNotification(
        process_id=process_id,
        parent_id=parent_id,
        type="assign_sample_peaks",
        status="pending",
        message=f"Assigning peaks for sample '{sample.sample_item_name}'.",
        data={
            "sample_item_id": sample_item_id,
            "peak_assignment_run_id": run.peak_assignment_run_id,
            "_user_id": user_id,
        },
    )

    try:
        # -- Load every observed peak of the sample
        peaks_df = _load_sample_peaks(sample)
        await send_progress_user_notification(notification, 0.1)

        # -- Stage A: database-first assignment from the known target library
        stage_a_assignments: list[dict] = []
        target_isotopes_df = await _fetch_known_target_isotopes(
            sample, match_params.isotope_abundance_threshold
        )
        if not target_isotopes_df.empty:
            match_isotope_df = await compute_match_isotopes(
                filename=sample.filename,
                target_isotopes_df=target_isotopes_df,
                polarity=sample.polarity,
            )
            # Gate raw matches by the sample's match parameters, exactly as the
            # targeted Match pipeline does: this zeroes the score of peaks whose
            # m/z error, isotope-ratio error, or intensity falls outside
            # tolerance. Without it a peak tens of ppm off a target would be
            # tiered "identified" here while the Match tab reports no match.
            if not match_isotope_df.empty:
                match_isotope_df = apply_match_params(match_isotope_df, match_params)
                # Deliberately score Stage A with the fit score (score_pattern_v2):
                # the peak-centric engine's scoring engine is the ion-level fit
                # quality, not the targeted matcher's per-isotopologue term. Runs
                # after gating so tolerance/intensity cuts carry into the fit.
                match_isotope_df = score_ions_by_fit(match_isotope_df)
            instrument = get_instrument_type(sample.filename)
            # Load this instrument's confidence calibration from the D6 store (active DB row,
            # else the in-code provisional curve, else None -> uncalibrated). Passing it in keeps
            # the engine DB-free; its corroboration_weights drive the P3 adduct fold-in.
            calibration = await load_calibration(instrument, SCORE_VERSION)
            stage_a_assignments = invert_matches_to_peak_assignments(
                match_isotope_df,
                sample_item_id=sample_item_id,
                peak_assignment_run_id=run.peak_assignment_run_id,
                possible_threshold=config.candidate_threshold,
                probable_threshold=config.identified_threshold,
                max_alternatives=config.max_alternatives,
                instrument=instrument,
                calibration=calibration,
            )
        runtime.logger.info(
            f"Stage A assigned {len(stage_a_assignments)} of {len(peaks_df)} "
            f"peaks from the known target library"
        )
        await send_progress_user_notification(notification, 0.4)

        # -- Stage B: untargeted composition search for the remainder
        assigned_peak_ids = {
            assignment["sample_peak_id"] for assignment in stage_a_assignments
        }
        stage_b_assignments: list[dict] = []
        if config.run_untargeted:
            remainder_df = peaks_df[
                ~peaks_df["sample_peak_id"].isin(assigned_peak_ids)
                & (peaks_df["intensity"] >= config.peak_intensity_threshold)
                & (peaks_df["intensity"] > 0)
            ]
            # Composition enumeration cost scales with peak count; bound the
            # stage to the most intense unexplained peaks.
            remainder_df = remainder_df.nlargest(
                config.max_untargeted_peaks, "intensity"
            ).sort_values("mz")

            notations, mechanism_id_by_notation = await _fetch_untargeted_ionizations(
                sample
            )
            if remainder_df.empty or not notations:
                skip_reason = (
                    "no eligible unassigned peaks"
                    if remainder_df.empty
                    else "no polarity-compatible ionization mechanisms"
                )
                runtime.logger.info(f"Skipping untargeted stage: {skip_reason}")
            else:
                formula_ranges, _ = to_explicit_isotope_format(config.formula_ranges)
                search_config = CompositionSearchConfig(
                    ionizations=",".join(notations),
                    mass_range_ppm=config.mz_precision_ppm,
                    element_count_ranges=formula_ranges,
                    use_unsaturation=True,
                    min_unsaturation=-1000.0,
                    max_unsaturation=10000.0,
                )
                # assign_compositions is synchronous and CPU-bound (recursive
                # composition enumeration over up to max_untargeted_peaks). This
                # runs as a background task on the API event loop, so offload it
                # to a worker thread to avoid blocking every other request and
                # the progress notifications for the duration of the search.
                matches_df, _ = await asyncio.to_thread(
                    assign_compositions,
                    remainder_df[["mz", "intensity"]].reset_index(drop=True),
                    search_config,
                )
                peak_lookup = {
                    float(row.mz): (str(row.sample_peak_id), float(row.intensity))
                    for row in remainder_df.itertuples(index=False)
                }
                stage_b_assignments = untargeted_matches_to_peak_assignments(
                    matches_df,
                    peak_lookup=peak_lookup,
                    sample_item_id=sample_item_id,
                    peak_assignment_run_id=run.peak_assignment_run_id,
                    possible_threshold=config.candidate_threshold,
                    probable_threshold=config.identified_threshold,
                    mechanism_id_by_notation=mechanism_id_by_notation,
                    formula_formatter=to_custom_element_format,
                    max_alternatives=config.max_alternatives,
                )
                runtime.logger.info(
                    f"Stage B assigned {len(stage_b_assignments)} of "
                    f"{len(remainder_df)} remaining peaks via untargeted search"
                )
        await send_progress_user_notification(notification, 0.8)

        # -- Persist the complete ledger: one row per observed peak
        assigned_peak_ids.update(
            assignment["sample_peak_id"] for assignment in stage_b_assignments
        )
        unassigned_df = peaks_df[~peaks_df["sample_peak_id"].isin(assigned_peak_ids)]
        unassigned_assignments = build_unassigned_assignments(
            unassigned_df,
            sample_item_id=sample_item_id,
            peak_assignment_run_id=run.peak_assignment_run_id,
        )

        all_assignments = (
            stage_a_assignments + stage_b_assignments + unassigned_assignments
        )
        # Insert owners before children: owner_peak_assignment_id is a
        # self-referential FK validated per row during the bulk insert.
        all_assignments.sort(
            key=lambda row: row["owner_peak_assignment_id"] is not None
        )
        if all_assignments:
            async with async_session() as session:
                await session.execute(insert(PeakAssignment), all_assignments)
                await session.commit()

        await _finalize_run(run.peak_assignment_run_id, "completed")
        await send_progress_user_notification(notification, 1.0)

        message = (
            f"Assigned peaks for sample '{sample.sample_item_name}': "
            f"{len(stage_a_assignments)} from the target library, "
            f"{len(stage_b_assignments)} untargeted, "
            f"{len(unassigned_assignments)} unassigned "
            f"({len(all_assignments)} peaks total)."
        )
        runtime.logger.info(message)
        return {
            "status": "success",
            "message": message,
            "data": {
                "peak_assignment_run_id": run.peak_assignment_run_id,
                "total_peaks": len(all_assignments),
                "database_assigned": len(stage_a_assignments),
                "untargeted_assigned": len(stage_b_assignments),
                "unassigned": len(unassigned_assignments),
            },
            "_notification_data": {
                "sample_batch_id": sample.sample_batch_id,
                "sample_item_id": sample_item_id,
                "peak_assignment_run_id": run.peak_assignment_run_id,
            },
        }
    except Exception as e:
        await _finalize_run(run.peak_assignment_run_id, "failed", error=str(e))
        runtime.logger.error(
            f"Peak assignment run '{run.peak_assignment_run_id}' failed: {e}"
        )
        raise


async def auto_assign_sample_peaks(
    sample_item_id: str,
    user_id: int | None = None,
    parent_id: str | None = None,
) -> None:
    """Run Stage-A-only peak assignment as part of sample auto-processing.

    The auto-processing pipeline runs the assignment engine database-first
    (`run_untargeted=False`) only: Stage A reuses the matcher that already ran
    for the sample and is cheap on the small ACQUISITION target collections,
    whereas Stage B (untargeted composition enumeration) is the documented
    scaling risk and stays opt-in via an explicit sample/batch run.

    A failure here must never fail auto-processing - the sample is created,
    calibrated, and matched regardless - so any error is logged and swallowed.
    Called with ``independent_transaction=False`` so its progress nests under
    the parent process and no per-sample success toast is emitted; the parent
    orchestrator owns the ``peak_assignment_reload`` UI refresh.

    :param sample_item_id: ID of the sample item to assign
    :param user_id: Current user triggered operation (for user notifications)
    :param parent_id: Parent process identifier for progress nesting
    """
    try:
        await assign_sample_peaks(
            sample_item_id=sample_item_id,
            config=PeakAssignmentConfig(run_untargeted=False),
            independent_transaction=False,
            user_id=user_id,
            process_id=gen_id(8),
            parent_id=parent_id,
        )
    except Exception as e:
        # Isolate assignment failures from the processing lifecycle.
        runtime.logger.warning(
            f"Auto peak assignment failed for sample '{sample_item_id}': {e}"
        )
