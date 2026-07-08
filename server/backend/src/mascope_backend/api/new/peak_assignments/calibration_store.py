"""Backend calibration store (D6): load the assignment-confidence calibration from the DB.

The confidence calibration (score -> P(correct) Platt curve + per-adduct corroboration log-odds)
lives per instrument. This loader reads the active row from ``assignment_calibration`` for the
given instrument + fit-score version and returns a :class:`mascope_tools...Calibration`; when the
table has no active row it falls back to the in-code provisional curve
(``mascope_tools...calibration_for``). So a deployment can refit and override the shipped default
without a code change, while an empty store still behaves exactly as before.

``mascope_tools`` stays DB-free: it defines the ``Calibration`` value object and the pure
``apply_calibration`` / ``apply_corroboration`` math; this backend module is the only place that
knows about the DB table.
"""

from __future__ import annotations

from sqlalchemy import select

from mascope_backend.db import AssignmentCalibration, async_session
from mascope_tools.composition.calibration import Calibration, calibration_for


def _to_calibration(row: AssignmentCalibration) -> Calibration:
    return Calibration(
        a=row.a,
        b=row.b,
        instrument=row.instrument,
        n_pos=row.n_pos,
        n_neg=row.n_neg,
        ece=row.ece,
        fit_utc=row.fit_utc.isoformat() if row.fit_utc else None,
        source=row.source,
        provisional=row.provisional,
        corroboration_weights=dict(row.corroboration_weights)
        if row.corroboration_weights
        else None,
    )


async def load_calibration(
    instrument: str | None, score_version: int
) -> Calibration | None:
    """The calibration for ``(instrument, score_version)``: the active DB row if present, else
    the in-code provisional curve, else ``None`` (uncalibrated instrument).

    ``None`` stays a first-class answer -- callers must report the assignment uncalibrated rather
    than borrow another instrument's curve. A DB row always wins over the in-code default, so
    refitting a curve (a new active row) overrides the shipped provisional without code changes."""
    if not instrument:
        return None
    inst = str(instrument).lower()
    async with async_session() as session:
        row = (
            (
                await session.execute(
                    select(AssignmentCalibration)
                    .where(
                        AssignmentCalibration.instrument == inst,
                        AssignmentCalibration.score_version == score_version,
                        AssignmentCalibration.is_active.is_(True),
                    )
                    .order_by(AssignmentCalibration.created_utc.desc())
                )
            )
            .scalars()
            .first()
        )
    if row is not None:
        return _to_calibration(row)
    return calibration_for(inst)
