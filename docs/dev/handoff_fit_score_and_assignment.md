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
   peak-assignment-tables head). Legacy `match_ion` / `match_isotope.match_score`
   deliberately untouched. **Applied to `mascope_demo` (dev postgres) end-to-end**; the
   live API serves `fit_score`.
4. ✅ **Fit-scale tier bands (0.8 / 0.5).** `PeakAssignmentConfig.identified_threshold`
   (0.8) / `candidate_threshold` (0.5); Stage A/B tier against them instead of the legacy
   `match_params` thresholds. Persisted on the run config; provisional (see below).
5. ✅ **Phase 3 P2 — candidate arbitration (core).**
   `mascope_tools.composition.arbitration.arbitrate_candidates`: competes a peak's
   candidates by **fit × plausibility**, emits a normalised confidence, flags ties
   (Schymanski L5). Unit-tested; `assignment_confidence.md` §4 (P2 progress).
6. ✅ **Live end-to-end on real demo spectra.** Migrated `mascope_demo` to head and ran
   `assign_sample_peaks` over all 161 demo samples. `fit_score` median ≈ 0.95; tiers band
   cleanly; Stage A winners chosen by fit × plausibility with confidence/tie in
   `provenance`. Data sits in `mascope_demo.peak_assignment` for the UI.
7. ✅ **P2 confidence calibration (pipeline; data provisional).**
   `mascope_tools.composition.calibration`: `Calibration` (provenance-carrying),
   `fit_calibration` (Platt + held-out ECE, refuses too-little data), `apply_calibration`,
   `calibration_error`, per-instrument `calibration_for`. **Honest fallback:** no curve for
   an instrument → `p_correct=null, calibrated=false` (TOF today); one **provisional
   Orbitrap** curve (a=5.74, b=-3.36, held-out ECE 0.029) fit from the demo bundle via
   `arbitration_eval.py --fit-calibration`. Wired into the engine → `provenance.p_correct /
   calibrated / calibration`. Labels = reference-confirmed identities (Schymanski L1) vs
   decoys — the reference-dataset link + basis for future user self-calibration. See
   `assignment_confidence.md` §4 + `how-it-works/peak_assignment.md`.
8. ✅ **How-it-works docs** — new user-facing `how-it-works/peak_assignment.md` (fit score,
   plausibility, arbitration, calibration, tiers) with citations; `matching.md` TODO
   resolved.
9. ✅ **Peak-ownership tolerance fix** — a peak is only OWNED by an isotopologue whose
   pairing is within tolerance (`invert_matches_to_peak_assignments` requires a positive
   gated intensity). The targeted matcher pairs within a wide 0.5 Da window; without this a
   trace isotopologue grabbed an out-of-tolerance peak (up to ~1500 ppm off on the demo,
   ~71% of Stage A rows), inherited its ion's tier, and blocked that peak's correct
   assignment. Out-of-tolerance pairings now fall through to Stage B / unassigned.
   Unit-tested.

## 6a. Roadmap / next steps (priority order)

**A — correctness / verification (near-term)**
- **A1. Verify the ownership fix (#9).** ✅ *Verified read-only on the demo* (no DB writes,
  no interference): running the real matcher → gating → `invert` on 8 samples (both
  polarities), Stage A ownership drops **5078 → 1519 peaks — 70.1% were out-of-tolerance
  steals**, now released to Stage B / unassigned (matches the 71% dataset-wide finding).
  Remaining: a **persisted** re-run so the corrected data is UI-browsable — needs the
  `isotope_formula` migration applied to the run DB; prefer an isolated env
  (`mascope dev run --instance`; note the per-env filestore) over the shared demo stack.
- **A2. (optional) Two-tier claim tolerance** — a looser "claim" tolerance (~3–5 ppm) so
  genuinely borderline real isotopes are not released while the strict tolerance still gates
  the score. Only if borderline isotopes are seen dropping.

**B — fit-score model**
- **B3. Mass-term over-penalty — investigated (golden set).** Conclusion: **no
  distribution-level fix is warranted for `Br3-`.** Empirically the mass-error core is
  m/z-flat (~0.13–0.18 ppm), with **no m/z σ growth**, **no m/z offset** (Br3-'s region
  signed-mean ~0), and only a mild high-intensity (space-charge) uptick; a **Student-t** term
  scores Br3- *lower* (its peaks are at the ~1.4 σ shoulder, not the deep tail). Br3- is a
  genuine **mass-accuracy outlier** and ~0.6 is honest (calibrated confidence ~0.57 agrees).
  The one **data-supported** refinement (unrelated to Br3-): **SNR-aware mass σ** — weak
  peaks have ~3× larger errors (0.22 vs 0.07 ppm) but are scored against the tight bulk σ;
  loosen the per-peak mass σ with 1/SNR (as the intensity term already does). *Decision
  needed:* implement the SNR-aware mass σ (a real improvement, does not lift Br3-), accept
  Br3- as honest, or treat "perfect pattern should offset moderate mass error" as a
  product-level mass-vs-pattern re-weighting (a deeper tradeoff). See `fit_score.md`
  §Limitations.

**C — finish Phase 3 P2 (science)**
- **C4. Curated calibration data** — a proper Orbitrap reference set to replace the
  provisional curve, and a **TOF golden set** so TOF stops being uncalibrated. Positives =
  reference-standard identities (Schymanski L1); negatives = decoys — tightly tied to the
  reference dataset.
- **C5. Extend arbitration + calibration to Stage B** once untargeted candidates carry
  comparable per-candidate fits.

**D — product / data-gated decisions**
- **D6. Persisted, user-refittable per-instrument calibration store** (the deferred DB
  table) + the "calibrate my instrument" UX.
- **D7. Recalibrate the fit-scale tier bands** (currently the 0.8/0.5 estimates) per
  instrument — a "what users see" decision.

**E — ops**
- **E8. Run the rename migration in prod/CI** and the migration test suite
  (`server/backend/tests/migrations/`, ephemeral drift DB — passed locally). Resolve the
  **worktree/main alembic split**: the CLI migration check (`mascope dev migrate`) runs
  alembic from the *main* checkout's venv, so it cannot see this branch's migrations
  (locally applied via a direct alembic run against the worktree code).

**F — later phases**
- **F9. P3 — spectral-neighbourhood corroboration** (adduct/isotope/in-source-fragment
  grouping; CAMERA/IPA) — the biggest untapped confidence source.
- **F10. P4 — context & levels** — retention-time / ionization priors + a reported
  Schymanski/MSI identification **level** alongside the confidence.

*Doc discipline:* record the plan here as it evolves; document each **implemented** feature
in `docs/user/how-it-works/` with its literature citations.

## 7. Environment / ops notes

- **Running the worktree's code:** the `.venv` is an editable install pointing at the
  *main* checkout, so to import THIS worktree's code you must put its `src` dirs on
  `PYTHONPATH` ahead of the `.pth` entries. Test invocation pattern used here:
  `PYTHONPATH="<worktree>/server/backend/src;<worktree>/libraries/*/src;…" python -m pytest …`.
- **Demo DB:** Postgres in the `mascope_dev_postgres` docker container (`mascope_demo`
  database) backs the golden-dataset validation.
- The fit score was validated end-to-end on the demo (median fit 0.94, max 1.0; scores
  scale monotonically with isotopic corroboration) — see `DESIGN.md` for the numbers.
