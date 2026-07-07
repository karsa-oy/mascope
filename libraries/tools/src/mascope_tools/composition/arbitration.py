"""Candidate arbitration (assignment-confidence Phase 3, P2).

The fit score measures how well the data fit ONE candidate; it is competitor-blind
(``fit_score.md``). Arbitration is the layer that, for a single peak, *competes* the
candidates that all fit the mass and decides which is the real assignment -- exactly
the problem the field frames as "accurate mass alone cannot determine a composition"
(Kind & Fiehn 2006). Here we combine two independent, one-directional pieces of
evidence:

- **fit** -- ``score_pattern_v2`` (mass + isotope pattern + SNR detectability), and
- **chemical plausibility** -- the graded Seven Golden Rules score
  (``heuristic_filter.formula_plausibility``),

as their product (``evidence = fit x plausibility``), then reports a per-candidate
**confidence** (the evidence normalised across the peak's candidates) and is honest
about **ties** -- when two candidates are within ``tie_tol`` we say so rather than
inventing a winner (Schymanski et al. 2014, L5).

Design rule (``assignment_confidence.md`` S3): the dependency points one way. This
layer imports the fit score's *values* and the chemistry plausibility; neither of
those imports arbitration. Calibrating the confidence to a true P(correct) per
instrument and a target-decoy FDR are the remaining P2 work; the ranking + the honest
tie report are here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from mascope_tools.composition.heuristic_filter import formula_plausibility


# Two candidates whose evidence differs by at most this are reported as a tie rather
# than ranked as a confident winner/loser. Absolute tolerance on evidence (in [0, 1]).
DEFAULT_TIE_TOL = 0.05


@dataclass(frozen=True)
class ArbitratedCandidate:
    """One candidate after arbitration, for a single peak."""

    formula: str
    fit_score: float
    plausibility: float
    evidence: float  # fit_score * plausibility
    confidence: float  # evidence normalised across the peak's candidates -> [0, 1]
    rank: int  # 1 = best evidence
    is_tie: bool  # within tie_tol of the best evidence (an unresolved competitor)


def _as_formula_fit(candidate: Any) -> tuple[str, float]:
    """Accept a candidate as a ``{"formula", "fit_score"}`` mapping or a
    ``(formula, fit_score)`` pair. ``match_score`` is accepted as an alias for
    ``fit_score`` during the rename transition."""
    if isinstance(candidate, dict):
        formula = candidate.get("formula")
        fit = candidate.get("fit_score", candidate.get("match_score"))
    else:
        formula, fit = candidate
    try:
        fit = float(fit)
    except (TypeError, ValueError):
        fit = 0.0
    if not (fit == fit) or fit < 0.0:  # NaN or negative -> no evidence
        fit = 0.0
    return str(formula), fit


def arbitrate_candidates(
    candidates: Iterable[Any],
    *,
    tie_tol: float = DEFAULT_TIE_TOL,
) -> list[ArbitratedCandidate]:
    """Compete a single peak's candidates by ``fit x plausibility``.

    :param candidates: The peak's candidates, each a ``{"formula", "fit_score"}``
        mapping (``match_score`` accepted as an alias) or a ``(formula, fit_score)``
        pair. ``formula`` is the NEUTRAL formula (plausibility is a neutral-chemistry
        judgement, as produced by ``find_compositions`` before ionization).
    :param tie_tol: Evidence gap at or below which the runner-up is flagged a tie.
    :returns: The candidates as :class:`ArbitratedCandidate`, best evidence first.
        ``confidence`` sums to 1 across candidates with positive evidence; when no
        candidate has any evidence every ``confidence`` is 0 and every ``is_tie`` is
        True (nothing to distinguish). Deterministic; ties broken by descending fit
        then formula for a stable order.
    """
    scored: list[tuple[str, float, float, float]] = []
    for cand in candidates:
        formula, fit = _as_formula_fit(cand)
        plaus = formula_plausibility(formula)
        scored.append((formula, fit, plaus, fit * plaus))
    if not scored:
        return []

    # Best evidence first; stable, deterministic tie-break (fit desc, then formula).
    scored.sort(key=lambda t: (-t[3], -t[1], t[0]))
    total = sum(t[3] for t in scored)
    best_evidence = scored[0][3]

    out: list[ArbitratedCandidate] = []
    for rank, (formula, fit, plaus, evidence) in enumerate(scored, start=1):
        confidence = evidence / total if total > 0 else 0.0
        # A candidate is "tied" when it sits within tie_tol of the best evidence and
        # is not the sole contender. When there is no evidence at all, everything ties.
        near_best = (best_evidence - evidence) <= tie_tol
        is_tie = near_best and (
            total <= 0 or sum(1 for t in scored if (best_evidence - t[3]) <= tie_tol) > 1
        )
        out.append(
            ArbitratedCandidate(
                formula=formula,
                fit_score=fit,
                plausibility=plaus,
                evidence=evidence,
                confidence=confidence,
                rank=rank,
                is_tie=is_tie,
            )
        )
    return out
