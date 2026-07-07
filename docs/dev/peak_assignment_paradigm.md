`KARSA MASCOPE - DESIGN DOC - PEAK-CENTRIC ASSIGNMENT PARADIGM`

# Peak-Centric Assignment: Design & Implementation Plan

## Purpose

Mascope was built for **targeted analysis**: a curated list of target
compositions is matched against detected peaks in each sample. This document
plans the **paradigm shift** to **peak-centric assignment** - assigning a
chemical composition to *every* peak in each sample, first from the database of
known compositions and then via untargeted composition assignment for the
remainder.

It is an engineering design and phased plan, not a user guide. It records the
current architecture as-is, the assets already in the tree, the proposed data
model and engine, and the sequencing of work.

---

## 1. Current pipeline (targeted, as-is)

The system is anchored on **targets**, not peaks. The target model is a strict
downward tree ([models.py](../../server/backend/src/mascope_backend/db/models.py)):

```
TargetCollection            named list, attached to a SampleBatch (junction table)
  -> TargetCompound         neutral formula (+ CAS)
    -> TargetIon            compound + IonizationMechanism -> ion formula
      -> TargetIsotope      one isotopologue: mz, relative_abundance, resolution
```

Target ions and isotopes are generated from a compound's neutral formula in
[target_ions_compute.py](../../server/backend/src/mascope_backend/api/controllers/target/lib/compute/target_ions_compute.py)
(IsoSpec isotopologue prediction).

The matching engine
([compute/isotopes.py](../../libraries/match/src/mascope_match/compute/isotopes.py))
runs **target-first**. For each target isotope it loads sample peaks within
+/- 0.5 Da, assigns the nearest peak under per-ion constraints (a peak is unique
within an ion, m/z ordering within an ion is preserved, the higher-abundance
isotope wins a contested peak), and scores each isotope:

```
match_score = abundance_term * mz_term
abundance_term = 1 - min(1, |match_abundance_error|)
mz_term        = max(0, 1 - |match_mz_error_ppm| / 100)
```

Per-isotope results are written as `MatchIsotope` rows, then aggregated up into
`MatchIon` / `MatchCompound` / `MatchCollection` / `MatchSample`
([match_aggregate.py](../../server/backend/src/mascope_backend/api/controllers/match/lib/match_aggregate.py)),
each carrying a `match_category` (0 no / 1 possible / 2 probable; default
thresholds 0.7 / 0.8). Orchestration is `rematch_sample`, a background task in
[match_controller.py](../../server/backend/src/mascope_backend/api/controllers/match/match_controller.py).

### Two facts that dominate the redesign

1. **Measured peaks do not live in the database.** They are stored per-sample in
   zarr/parquet files and read via `mascope_file.io` / `mascope_signal.compute`
   (see [samples_peaks.py](../../server/backend/src/mascope_backend/api/controllers/samples/lib/samples_peaks.py)).
   A peak is identified by `sample_peak_id`, a stable string id within a file.
   `MatchIsotope` **denormalizes** the peak's mz/intensity/tof onto its own row
   and keys back to the peak only by `sample_peak_id`. There is no `sample_peak`
   table.

2. **A peak with no nearby target is never examined.** The target list is the
   driver, so everything not on a list is invisible. This is precisely what the
   paradigm shift inverts.

---

## 2. Assets already in the tree

The untargeted chemistry is largely already implemented inside Mascope; the gap
is persistence, arbitration, and productization - not the science.

- **`mascope_tools.composition`** - a complete untargeted engine
  ([finder.py](../../libraries/tools/src/mascope_tools/composition/finder.py),
  [heuristic_filter.py](../../libraries/tools/src/mascope_tools/composition/heuristic_filter.py)):
  - `find_compositions(mz, config)` enumerates valence-legal neutral formulas
    within a ppm tolerance across ionization mechanisms (recursive search with
    mass pruning and DBE bounds).
  - `apply_heuristic_rules` applies valence / Senior / element-ratio /
    known-chemical-space filters.
  - `predict_isotopes` + `score_pattern` do isotope-envelope scoring with the
    **same maths** the targeted matcher uses. The consolidated **fit score**
    (`score_pattern_v2`, detectability-gated + SNR- and resolution-aware) is the
    scoring engine for both stages — see
    [`fit_score.md`](../../libraries/tools/docs/fit_score.md).
  - `assign_compositions(peaks_df, config, heuristics)` already performs
    **whole-spectrum, one-row-per-peak assignment**: enumerate -> filter ->
    isotope-match -> pick best -> mark isotope children -> leave the rest `---`.

- **`api/new/cheminfo`**
  ([service.py](../../server/backend/src/mascope_backend/api/new/cheminfo/service.py))
  already exposes `find_compositions` over the API for a single m/z (on demand,
  not persisted). This is the seed of an untargeted endpoint.

- **`peaky`** (external repo `~/Documents/Repositories/peaky`, skill
  `mascope-peak-assign`) - the research-grade reference on top of the same
  `mascope_tools` scoring. It contributes hard-won logic the app currently lacks:
  a one-row-per-peak **ledger** with a single-owner-per-peak invariant,
  multi-pass **arbitration**, confidence **tiers**
  (Identified / Candidate / below-assignability), mass-**degeneracy** handling,
  offset-aware **calibration**, reagent/**context** presets, **batch merge**
  across time, and GKA / Van Krevelen **reporting**. It reads peaks via the SDK
  and writes **files, not the Mascope database**.

---

## 3. The core inversion: target-anchored -> peak-anchored

Today the unit of result is a `MatchIsotope` hanging off a `TargetIsotope`. To
assign all peaks, the unit of result must become the **observed peak**, with an
assignment that may or may not reference a known target. Nothing in the current
schema can hold "this peak got formula X" when X was discovered rather than
pre-listed.

### 3.1 Proposed persistence (least-invasive)

Keep files as the source of truth for raw peaks; mirror what `MatchIsotope`
already does (denormalize peak fields, key by `sample_peak_id`). Add two tables.

**`PeakAssignmentRun`** - one row per assignment run over a sample (or batch),
storing the engine version + full config (search ranges, heuristics,
reagent/context, ppm tolerances) so runs are reproducible and comparable.
Analogous to peaky's `manifest.json`. `PeakAssignment` rows FK to a run.

**`PeakAssignment`** - one row per observed peak in that run:

| column | meaning |
| --- | --- |
| `sample_item_id`, `sample_peak_id` | peak identity (FK + within-file id) |
| `sample_peak_mz` / `_intensity` / `_tof` | denormalized peak fields (as `MatchIsotope`) |
| `role` | `M0` / `iso_child` / `reagent` / `artifact` / `unassigned` |
| `assigned_formula` | committed neutral formula |
| `ion_formula`, `ionization_mechanism_id`, `isotope_label` | adduct + M0/M+1... |
| `source` | `database` / `untargeted` - which stage won the peak |
| `fit_score`, `mz_error_ppm`, `abundance_error` | evidence (`fit_score` = the fit-quality measurement, [`fit_score.md`](../../libraries/tools/docs/fit_score.md)) |
| `tier` | `identified` / `candidate` / `below_assignability` / `unassigned` |
| `target_compound_id`, `target_ion_id` (nullable) | set when the winner came from the known library |
| `owner_peak_assignment_id` (nullable) | an `iso_child` points at its `M0` |
| `alternatives` (JSON) | runner-up formulas + scores |
| `provenance` (JSON) | per-peak config/notes |

This yields a direct query - "every peak in sample X and its formula and
confidence" - without importing raw peak rows into Postgres. Crucially, the
nullable `target_compound_id` / `target_ion_id` is how **targeted analysis
becomes a view over peak assignments** rather than a separate subsystem: a
targeted result is just a peak assignment whose winner came from the curated
library.

### 3.2 Two-stage engine (database-first, then untargeted)

**Stage A - database / known.** Match every peak against the union of known
isotopologues (the existing target library, optionally plus a curated "known
compositions" reference set). The existing matcher already produces, per known
isotope, the `sample_peak_id` it hit and the score, so Stage A is mostly *reuse
`compute_match_isotopes` + invert the result* (group by `sample_peak_id`, pick
the best-scoring owner) and write `PeakAssignment` rows with `source=database`.

**Stage B - untargeted.** For peaks Stage A left unexplained, run
`mascope_tools.assign_compositions` (or `find_compositions` + `score_pattern` for
finer control) to enumerate candidates, filter by chemistry/context, score the
isotope envelope, and pick an owner. Persist winners + `alternatives` + tier.

**Global arbitration** (the genuinely new logic). Targeted matching never needed
"who owns this peak" because targets were curated. Untargeted assignment produces
many candidates per peak and many peaks per envelope, so it needs a global
single-owner-per-peak pass with isotope children attributed to their owner - this
is peaky's ledger invariant. The arbitration pass and the **confidence tiers**
(a richer replacement for `match_category` 0/1/2) are built once and reused
across both stages.

---

## 4. Phased implementation plan

Each phase is intended to land independently and leave the system shippable.

### Phase 0 - Foundations
- Add `PeakAssignmentRun` + `PeakAssignment` tables and an Alembic migration
  ([alembic/versions](../../server/backend/alembic/versions)).
- Peak identity = `(sample_item_id, sample_peak_id)` with denormalized
  mz/intensity/tof.
- Read API/endpoint: "peaks-with-assignments per sample." No assignment logic
  yet - just the schema and the read model.

### Phase 1 - Stage A (database-first)
- Build the "known isotope" set from the existing target library.
- Run the existing matcher peak-centrically; add the inversion/arbitration-to-peak
  step; persist `source=database` assignments.
- Background task + endpoint mirroring `rematch_sample`
  ([match_controller.py](../../server/backend/src/mascope_backend/api/controllers/match/match_controller.py)).

### Phase 2 - Stage B (untargeted)
- Wire `assign_compositions` for the unassigned remainder.
- Surface heuristic / context / reagent config (reuse peaky's context presets).
- Persist candidates + tiers; arbitrate Stage A vs Stage B ownership.

### Phase 3 - Arbitration & confidence
- Global single-owner-per-peak; isotope-child attribution.
- Tiers (identified / candidate / below-assignability / unassigned),
  alternatives, mass-degeneracy notes.
- Harvest peaky's `assignment/*` logic (arbitration, tiers, degeneracy,
  offset-aware calibration) into a backend module. The **science-based design + phased
  plan** for this layer (evidence layers, Schymanski/MSI levels, target-decoy
  calibration, references) is [`assignment_confidence.md`](assignment_confidence.md).

### Phase 4 - Batch level
- Cross-sample / time merge, homologous-series (GKA) detection, Van Krevelen,
  reporting - harvest peaky's `batch/*` and `reporting/*`.

### Phase 5 - Productization
- UI + CLI surfaces.
- Performance: a sample can carry thousands of peaks and enumeration cost is the
  scaling risk - cache, bound search ranges, reuse peaky's pruning.
- Reproducibility / versioning via `PeakAssignmentRun`.
- Fold the legacy targeted workflow in as a curated view over peak assignments.

---

## 5. Key design decisions

These are the forks that shape the work. Current recommendations are recorded so
the plan is actionable; revisit as phases land.

1. **Coexist vs. replace targeted.** *Recommend coexist.* Peak-centric assignment
   becomes the substrate; targeted analysis becomes a filtered view
   (`target_compound_id IS NOT NULL`). Targeted alarms/collections keep working
   and are not rewritten up front.

2. **Peaky: harvest vs. depend-on vs. reimplement.** *Recommend harvest.* Build
   on `mascope_tools.assign_compositions` as the spine and pull peaky's
   hard-won parts (arbitration, tiers, degeneracy, calibration, reagent contexts)
   into the backend incrementally. Peaky stays the reference and research surface;
   the app takes no runtime dependency on prototype-grade, file-oriented code.

3. **Peak persistence.** *Recommend keep files as source of truth* and denormalize
   peak fields onto `PeakAssignment` exactly as `MatchIsotope` already does -
   avoiding a heavy peak-table import.

---

## 6. Scope summary

Most of the chemistry already exists in `mascope_tools.composition` and is
proven out in peaky. The genuinely new engineering is:

- the two new tables + migration (Phase 0),
- the peak-centric **inversion** of Stage A (Phase 1),
- the global **ownership + tier arbitration** (Phase 3).

Everything else is wiring existing engines into a persisted, queryable,
reproducible result and progressively harvesting peaky's assignment quality
logic into the backend.
