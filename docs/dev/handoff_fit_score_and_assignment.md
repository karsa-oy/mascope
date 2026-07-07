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

**Landed since this handoff (all on `epic/peak-centric-assignment`):**

1. ✅ **Phase 3 chemistry — graded plausibility (P1).** `chemical_plausibility` /
   `formula_plausibility` in `heuristic_filter.py`: a per-candidate plausibility in
   `[0,1]` = Senior/RDBE (Rule 2) × element-ratio (Rules 4–5, Table 2) × heteroatom
   co-occurrence (Rule 6, Table 3), numbers verbatim from Kind & Fiehn 2007. Grades, does
   not gate; fail-open. Unit-tested + validated on the 91 demo formulas (only the
   over-saturated `C6H17NO4` scores 0). See `assignment_confidence.md` §4.
2. ✅ **Wired the fit score into the peak-centric engine's Stage A/B scoring.** Stage A:
   `engine.score_ions_by_fit` (deliberate ion-level `score_pattern_v2` per `target_ion_id`,
   post-gating). Stage B: uses the isotope-pattern fit score `assign_compositions` already
   computes (v1 degradation, no SNR). Both replace the crude `abundance_term·mz_term`.
   See `fit_score.md` §1a.
3. ✅ **Renamed `match_score` → `fit_score`** on the `PeakAssignment` surface: model column
   + range check constraint, `PeakAssignmentRecord` schema, engine output dicts,
   read-model, tests, and an Alembic migration (`b2e9d7c14a05`, chained from the
   peak-assignment-tables head). **Migration written but NOT run** — needs confirmation.
   Legacy `match_ion` / `match_isotope.match_score` deliberately untouched.

**Open (need a human / a live stack):**

4. **Run the rename migration** `b2e9d7c14a05` and the migration test suite
   (`server/backend/tests/migrations/`, ephemeral drift DB) — a DB-migrating operation,
   left for the human.
5. **Recalibrate the confidence-tier bands for the fit scale.** Stage A/B now score on the
   fit scale (a lone mass-only match scores low by design), but `tier_for_score` still uses
   the legacy `match_params` thresholds (0.8/0.7). DESIGN.md suggests v2 bands ≈ 0.8/0.5.
   This changes *what users see* (single-peak matches demote) → a product decision.
6. **Live end-to-end validation of Stage A.** `score_ions_by_fit` is unit-tested pure;
   its real-SNR path (filestore zarr → `compute_match_isotopes`) needs a demo-stack run to
   confirm end-to-end (the backend/integration suites need Postgres + the demo bundle).
7. **Phase 3 P2 — candidate arbitration + target-decoy FDR** (`assignment_confidence.md`):
   compete candidates by fit × plausibility, calibrate per instrument, emit a confidence.
8. **Rewrite the how-it-works user docs** (`docs/user/how-it-works/matching.md` TODO) once
   the pipeline settles.

## 7. Environment / ops notes

- **Running the worktree's code:** the `.venv` is an editable install pointing at the
  *main* checkout, so to import THIS worktree's code you must put its `src` dirs on
  `PYTHONPATH` ahead of the `.pth` entries. Test invocation pattern used here:
  `PYTHONPATH="<worktree>/server/backend/src;<worktree>/libraries/*/src;…" python -m pytest …`.
- **Demo DB:** Postgres in the `mascope_dev_postgres` docker container (`mascope_demo`
  database) backs the golden-dataset validation.
- The fit score was validated end-to-end on the demo (median fit 0.94, max 1.0; scores
  scale monotonically with isotopic corroboration) — see `DESIGN.md` for the numbers.
