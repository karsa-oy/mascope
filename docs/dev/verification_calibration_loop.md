# Interactive verification → the calibration golden set

*A design for a human-in-the-loop layer where users confirm or reject peak-centric
identifications in the UI, and those verdicts become the labelled golden set that fits each
instrument's confidence calibration. This closes the loop opened by the P2 calibration pipeline
([`assignment_confidence.md`](assignment_confidence.md)) and the D6 calibration store
([`handoff_fit_score_and_assignment.md`](handoff_fit_score_and_assignment.md)). Status: design only —
nothing here is built yet.*

## 1. Why

The confidence layer produces a calibrated probability `p_correct`, but its curve is only as good as
the labels it was fit on. Today one **provisional** Orbitrap curve ships, fit on a preliminary
demo set. The principled, sustainable source of labels is the users themselves: as an analyst
verifies identifications in the normal course of work, each verdict is a `(score, correct?)` label
for *their* instrument. Accumulated, those labels refit the calibration so `p_correct` means what it
says — per instrument, per reagent chemistry, and improving over time.

This is exactly the source `fit_calibration` already anticipates: positives are **confident
identifications** — most strongly, a compound confirmed against a **reference standard**
(Schymanski Level 1, [Schymanski et al. 2014][sch14]); negatives are confirmed-wrong assignments and
near-mass decoys.

## 2. What already exists (build on, don't reinvent)

- **A verification UX.** `MatchRating` (`db/models.py`: per `sample_item` + `target_ion`, a
  `rating` 0–2 plus `checklist` / `environment` JSON) and
  [`DialogMatchRating.vue`](../../server/frontend/src/lib/dialogs/DialogMatchRating.vue) already walk
  a user through a checklist ("is there a clear peak for each target isotope? do the timeseries
  agree?") and store a verdict. It targets the **legacy target-Match** workflow, not the new
  peak-centric assignments.
- **The calibration pipeline that consumes these labels.**
  [`calibration.py`](../../libraries/tools/src/mascope_tools/composition/calibration.py):
  `fit_calibration(scores, is_correct)` → a `Calibration` with held-out ECE; `MIN_CALIBRATION_LABELS`
  = 30 of each class.
- **The D6 store + loader.** `assignment_calibration` table (migration `d1a2c3b4e5f6`) and
  `calibration_store.load_calibration` (active row → in-code fallback). Writing a new active row
  *is* "recalibrate this instrument".
- **The score-eval decoy machinery** (`tooling/score_eval/`) for synthetic negatives.

So this feature is mostly **connecting existing parts into a loop**, plus one new table and one UI
control.

## 3. The loop

```
   assignment (p_correct, evidence)
        │
        ▼
   user verifies in the inspector  ──►  assignment_verification row
   (confirm / reject / unsure,           (verdict, evidence level,
    checklist, evidence level)            SCORE SNAPSHOT, verified_by, utc)
        ▲                                        │
        │                          aggregate per instrument (+ decoys for negatives)
        │                                        │
        │                                        ▼
   load_calibration  ◄── new active row ──  fit_calibration → Calibration (a,b,ece)
   (D6 store)              (assignment_calibration)
```

## 4. Design

### 4.1 Label semantics

A verification attaches to a specific assignment — the `(sample_peak, assigned formula, adduct)` —
and records:

- **verdict**: `confirmed` | `rejected` | `unsure`. `confirmed`/`rejected` are the calibration
  positives/negatives; `unsure` is captured but excluded from fitting.
- **evidence level** — *why* the user is confident, not just that they are. Roughly the Schymanski
  ladder: authentic reference standard (L1) › MS/MS or diagnostic fragments (L2) › RT + isotope +
  adduct corroboration (L2–L3) › visual review only (weak). This is load-bearing (see §5).
- **score snapshot** — the `fit_score`, `evidence`, and `p_correct` **at the moment of
  verification**. Assignments get recomputed on re-runs; the calibration pair must be pinned to the
  score the user actually judged, or the `(score, label)` mapping drifts.
- **checklist** JSON (reuse the Match dialog's structure), `verified_by`, `verified_utc`, and the
  `peak_assignment_run_id` for provenance.

### 4.2 Data model — `assignment_verification`

A new table (mirrors `MatchRating`, but keyed to the peak-centric result so it also covers
untargeted/Stage-B formulas that have no `target_ion`):

```
assignment_verification_id (pk)
sample_item_id            (fk, index)
peak_assignment_id        (fk, index) — the assignment verified
peak_assignment_run_id    — provenance of the snapshot
assigned_formula          — the compound/ion judged (survives re-runs, unlike a run-scoped id)
ionization_mechanism_id   — the adduct
verdict                   — confirmed | rejected | unsure
evidence_level            — enum (reference_standard | msms | corroborated | visual | ...)
fit_score, evidence, p_correct  — snapshot at verification time
checklist (JSON), environment (JSON)
verified_by (fk user), verified_utc
```

Keep every verdict (append-only, audit trail); the "current" verdict for an assignment is the
latest by `verified_utc`.

### 4.3 UI

A confirm / reject / unsure control in the peak-assignment inspector (design branch), opening the
existing checklist flow, prefilled with the assignment's isotopes + now the co-occurring adducts.
Surface the evidence-level choice explicitly. A batch/queue view ("assignments awaiting
verification", ranked to be useful — see §5 active learning) makes labelling efficient.

### 4.4 Feeding the calibration

Per instrument class, aggregate `confirmed` (positive) + `rejected` (negative) verifications, top up
negatives with near-mass decoys if needed, and when ≥ `MIN_CALIBRATION_LABELS` of each class exist,
run `fit_calibration` and write a new active `assignment_calibration` row (flipping the previous one
inactive). Show before/after held-out ECE so the user sees the improvement. The same accumulated
labels can refit the **per-adduct corroboration weights** (the offset-decoy benchmark generalises to
"confirmed multi-adduct compounds vs rejected ones").

## 5. The central risk: the confirmation-bias loop

**This is the design's whole point of failure.** If users confirm/reject based on the `p_correct`
Mascope shows them, the labels just echo the model; calibrating on them makes the curve *look*
perfect while learning nothing, and amplifies existing bias. Guardrails:

1. **Prefer evidence independent of the score.** Weight `reference_standard` (L1) labels far above
   `visual`-only ones — a standard is truth external to the fit. Consider fitting on L1/L2 only, and
   treating `visual` labels as low-weight or exploratory. The `evidence_level` field exists for this.
2. **Rejections are first-class.** Calibration needs confirmed-wrong, not only confirmations. Make
   "reject" as easy as "confirm", and combine user rejections with synthetic decoys for negatives.
3. **Label across the score range, not just the top.** The curve is under-constrained near the
   decision boundary; an **active-learning queue** should surface *mid-confidence* assignments to
   verify, not rubber-stamps of the obvious. Random spot-checks guard against blind spots.
4. **Audit + provisional gating.** Append-only, with who/when/evidence, so a fit can filter to
   trustworthy labels. Keep `provisional=True` until enough L1-grade labels exist; only then does the
   curve claim to be real.
5. **Don't show `p_correct` as the anchor during verification** (or de-emphasise it) so the judgment
   is about the *data*, not the number.

If these hold, the loop is a genuine ground-truth flywheel; if they don't, it's a self-fulfilling
prophecy. Everything else here is secondary to getting this right.

## 6. Phased plan

- **V1 — capture.** `assignment_verification` table + migration; confirm/reject/unsure control in the
  inspector with evidence level + score snapshot; read-only "my verifications" view. No auto-calibration
  yet — just start accumulating honest labels. (Guardrails 1, 2, 4, 5.)
- **V2 — close the loop.** Per-instrument aggregation + "recalibrate this instrument" →
  `fit_calibration` → new active D6 row, with before/after ECE. Finishes the D6 "calibrate my
  instrument" UX.
- **V3 — quality & scale.** Active-learning queue (guardrail 3), evidence-level weighting in the fit,
  refit of the corroboration weights, Schymanski-level surfacing on the assignment, and (optionally)
  cross-linking confirmations to `reference_compound` standards.

## 7. Open questions

- Verdict granularity: is the compound confirmed, or this specific adduct/ion? (Propose: the ion;
  aggregate to compound for corroboration.)
- Shared vs per-user calibration: whose labels fit the curve for a shared instrument? (Propose:
  workspace/instrument-scoped, with per-user attribution retained.)
- How to weight `visual` labels in the fit without letting them dominate (down-weight vs exclude).
- Re-verification when a re-run changes an assignment: keep the old snapshot label, or invalidate?

## References

- Schymanski, E. L. et al. *Identifying small molecules via high-resolution mass spectrometry:
  communicating confidence.* Environ. Sci. Technol. 2014, 48 (4), 2097–2098. [link][sch14]
- Platt, J. *Probabilistic outputs for support vector machines.* 1999 (Platt scaling).

[sch14]: https://pubs.acs.org/doi/10.1021/es5002105
