# Handoff — Fit Score & Assignment Confidence (peak-centric integration)

*Start here if you are picking up the "fit score + identification confidence" workstream.
Everything is landed on the `epic/peak-centric-assignment` branch.*

## 1. What this workstream is

Two things, kept deliberately separate:

- **Fit score** — a pure, reproducible *measurement* of how well a peak's data fits a
  candidate composition (mass, intensity, SNR-detectability, isotopes). Bounded `[0,1]`,
  `1.0` = perfect. **Competitor-blind**; makes no probability claim.
- **Identification confidence** — a *layered* system on top of the fit score (chemistry,
  spectral neighbourhood, instrument/context, calibration, arbitration) that decides
  *which* of several well-fitting candidates is real, and reports a confidence + level.

This is the science layer of the **peak-centric assignment** paradigm: assign a
composition to every peak — Stage A (known/database), Stage B (untargeted), then
arbitration into confidence tiers. The fit score is the **scoring engine** for both
stages; the confidence layers are the paradigm's **Phase 3** (tiers/arbitration).

## 2. Read these, in order

1. [`peak_assignment_paradigm.md`](peak_assignment_paradigm.md) — the peak-centric engine
   (Stage A/B, `PeakAssignment` tables, phased plan). The frame everything sits in.
2. [`reference_peak_assignment_convergence.md`](reference_peak_assignment_convergence.md) —
   how the reference compound DB feeds Stage A (formula-based match, one-to-many identity).
3. [`../../libraries/tools/docs/fit_score.md`](../../libraries/tools/docs/fit_score.md) —
   the fit score: the exact model (`score_pattern_v2`), math, parameters, references.
4. [`assignment_confidence.md`](assignment_confidence.md) — the confidence-layer **study +
   phased plan** (L0–L5, Schymanski/MSI levels, target-decoy calibration, references).
5. [`../../libraries/tools/docs/composition_assignment.md`](../../libraries/tools/docs/composition_assignment.md) —
   the composition enumeration + heuristic filtering pipeline.
6. `../../tooling/score_eval/DESIGN.md` — untracked scratch design with the detailed
   validation numbers/metrics (kept in the worktree, not committed).

## 3. Decisions already made — do not relitigate (rationale + where documented)

- **`match_score` is the FIT, not a probability.** Displaying the Platt-calibrated
  probability made a perfect match read ~0.87 and looked "unsure"; the raw fit is
  median ~0.92 / max 1.0 and matches intuition. The calibration is retained but belongs
  to the confidence layer. (`fit_score.md` §1; `assignment_confidence.md`.)
- **Rename in flight: `match_score` → `fit_score`** to say plainly it measures fit.
- **Legacy targeted path defaults to v1** (`MASCOPE_MATCH_SCORE_VERSION=1`). The fit score
  (`=2`) is adopted *deliberately* in the peak-centric engine, not by silently flipping the
  legacy default — per the epic's "coexist, don't replace" principle. v2 also degrades to
  v1 where a lighter aggregation path lacks per-isotopologue columns.
- **`rule_senior` (Golden Rule 2) fails open on radicals.** It rejects only the impossible
  (over-saturated / disconnectable) neutrals; odd-electron species can be genuine
  (APCI/APPI). Applies to NEUTRAL formulas only.

## 4. Data-quality findings to revisit (chemistry review)

Validated `rule_senior` against the 92 demo target compounds:
- **`C6H17NO4`** — over-saturated (17 H on a C6NO4 skeleton, max 15): impossible for any
  neutral. Almost certainly a target-list **data error**; fix at source.
- **`C9H15O6`, `C10H15O5`, `C10H17O7`, `Br`** — odd-electron radicals as neutrals (they now
  pass, fail-open). Confirm whether legitimate radical species or off-by-one-H entries.

## 5. Current state

- **Branch:** `epic/peak-centric-assignment`, tip `7ac10e2c`. This work is the range
  `ffe43123..7ac10e2c` (22 commits). **Not yet pushed** (do `git push origin
  epic/peak-centric-assignment`).
- **Tests:** `88 passed` across `server/backend/tests/unit/api/match`,
  `libraries/tools/tests`, and epic's `.../api/peak_assignments`.
- **Code map:**
  - Fit score: `libraries/tools/src/mascope_tools/composition/heuristic_filter.py`
    (`score_pattern_v2`, `calibrate_score`, `rule_senior`).
  - Backend adapter: `.../api/controllers/match/lib/match_score_v2.py` (`ion_score_v2`,
    `match_score_version`) and the dispatch in `.../match/lib/match_aggregate.py`.
  - Peak-centric engine (epic): `server/backend/src/mascope_backend/api/new/peak_assignments/`.
  - Eval harness: `tooling/score_eval/` (`make_candidates.py`, `score_eval.py`).

## 6. Next steps (priority order)

1. **Rename `match_score` → `fit_score`** — schema/API + the new `PeakAssignment` score
   column. Coordinated refactor.
2. **Wire the fit score into the peak-centric engine's Stage A/B scoring** (it currently
   uses the older `score_pattern`).
3. **Phase 3 — confidence layers**: start with the chemistry layer (graded plausibility;
   `assignment_confidence.md` P1), then candidate arbitration + target-decoy FDR (P2).
4. **Rewrite the how-it-works user docs** (`docs/user/how-it-works/matching.md` has a
   maintainer TODO) once the pipeline settles.

## 7. Environment / ops notes

- **Running the worktree's code:** the `.venv` is an editable install pointing at the
  *main* checkout, so to import THIS worktree's code you must put its `src` dirs on
  `PYTHONPATH` ahead of the `.pth` entries. Test invocation pattern used here:
  `PYTHONPATH="<worktree>/server/backend/src;<worktree>/libraries/*/src;…" python -m pytest …`.
- **Demo DB:** Postgres in the `mascope_dev_postgres` docker container (`mascope_demo`
  database) backs the golden-dataset validation.
- The fit score was validated end-to-end on the demo (median fit 0.94, max 1.0; scores
  scale monotonically with isotopic corroboration) — see `DESIGN.md` for the numbers.
