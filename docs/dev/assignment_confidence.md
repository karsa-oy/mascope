# Peak Assignment & Identification Confidence — Study, Design and Plan

*A science-based, layered architecture for going from a peak to a confident chemical
identification. This document sets the scientific framing, surveys the relevant
literature, states where we are today, defines how the work is organized, and lays out
phased next steps.*

> **Status of today's heuristics.** peaky's current assignment logic (formula
> enumeration + a partial set of chemical filters + a heuristic ranking) is a
> **proof-of-concept spike**. It works, but it is not yet the structured, evidence-based
> system described here. This document is the target architecture it should grow into.

## 0. How this work is organized

This work lands on the **`epic/peak-centric-assignment`** integration branch, where it is
the science layer of the peak-centric paradigm
([`peak_assignment_paradigm.md`](peak_assignment_paradigm.md)). Two cleanly separable
tracks sit on top of epic:

| Track | Scope | Maps to |
|---|---|---|
| **Fit score** (the measurement) | the consolidated fit score (`score_pattern_v2`), its backend wiring, SNR/satellite plumbing, and [`fit_score.md`](../../libraries/tools/docs/fit_score.md) | the **scoring engine** for peak-centric Stage A/B; the `fit_score` column |
| **Assignment confidence** (this doc + the layers) | §2: chemistry, spectral-neighbourhood, instrument/context, probabilistic integration, arbitration, level reporting | the **tier + arbitration layer** (paradigm-doc **Phase 3** "harvest peaky's arbitration/tiers/calibration") |

**Design rule that keeps them separable:** the fit score never imports from the confidence
layers, and competitor-awareness / chemistry / context never get folded back into the
score. The dependency points one way — confidence builds on fit, not the reverse.

**Legacy coexistence.** The legacy targeted match keeps its v1 behaviour by default
(`MASCOPE_MATCH_SCORE_VERSION=1`); the fit score is adopted *deliberately* as the
peak-centric engine's scoring, per the epic's "coexist, don't replace" principle — it is
not a silent flip of the legacy default.

## 1. The core premise

A mass spectrometer measures *mass and intensity*, not *identity*. The foundational
result of the field is that **accurate mass alone — even sub-ppm — cannot uniquely
determine an elemental composition**, and that isotope-pattern information is worth more
than another order of magnitude of mass accuracy
([Kind & Fiehn 2006](https://bmcbioinformatics.biomedcentral.com/articles/10.1186/1471-2105-7-234)).
It follows that identification is fundamentally a problem of **accumulating independent
evidence** and **arbitrating between candidates that all fit the mass**.

This gives us a clean separation of concerns:

```
   measurement              evidence layers                       decision
 ┌──────────────┐   ┌───────────────────────────────┐   ┌──────────────────────┐
 │  FIT SCORE   │ → │ chemistry · spectral context · │ → │  identification:     │
 │ (pure math,  │   │ instrument · orthogonal data   │   │  ranked candidate +  │
 │ per candidate│   │ (each a calibrated likelihood) │   │  confidence + level  │
 │  likelihood) │   └───────────────────────────────┘   └──────────────────────┘
 └──────────────┘
```

- The **fit score** ([`fit_score.md`](../../libraries/tools/docs/fit_score.md)) is the
  reproducible measurement: *how well does the data fit this candidate's predicted
  pattern?* It is competitor-blind and makes no probability claim.
- The **confidence layers** add everything else we know — chemistry, the spectral
  neighbourhood, the instrument, orthogonal measurements — each ideally expressed as a
  likelihood or a calibrated probability.
- The **decision layer** combines the evidence into a posterior over candidates, picks
  the assignment, and reports a **calibrated confidence and an identification level**.

The output semantics should follow the community-standard **confidence-level schemes**:
the HR-MS levels of
[Schymanski et al. 2014](https://pubs.acs.org/doi/10.1021/es5002105) (Level 1 confirmed by
reference standard → Level 5 exact mass of interest) and the broader Metabolomics
Standards Initiative reporting standards
([Sumner et al. 2007](https://doi.org/10.1007/s11306-007-0082-2)). We should report a
*level*, not just a number, because that is how the field communicates identification
confidence.

## 2. The layers

Each layer below states its **scientific basis** (with references), **where we are
today**, and **the gap**.

### L0 — Candidate generation (formula enumeration)
*Basis.* Enumerate every elemental composition whose ion m/z lands within the mass
tolerance, per ionization channel. This is the classic "money-changing problem" of mass
decomposition ([Böcker & Lipták 2007](https://doi.org/10.1007/s00453-007-0162-8); used in
SIRIUS, [Böcker et al. 2009](https://academic.oup.com/bioinformatics/article/25/2/218/218950)).
*Today.* `mascope_tools.composition.finder.find_compositions` — bounded recursive
tree-search with mass-domain pruning (see
[`composition_assignment.md`](../../libraries/tools/docs/composition_assignment.md)). **Solid.**
*Gap.* None fundamental; ensure adduct/ionization channels are complete and configurable.

### L1 — Chemical plausibility (the Seven Golden Rules)
*Basis.* Most mass-degenerate formulas are chemically impossible or implausible. The
**Seven Golden Rules** ([Kind & Fiehn 2007](https://bmcbioinformatics.biomedcentral.com/articles/10.1186/1471-2105-8-105))
codify this: (1) element-count limits, (2) LEWIS/SENIOR valence rules (integer,
non-negative ring-and-double-bond equivalents; a chemically connectable graph must exist),
(3) isotope pattern, (4) H/C ratio bounds, (5) N/O/P/S-to-C ratio bounds, (6) element-ratio
*probabilities* from large compound databases, (7) presence/co-occurrence of certain
elements.
*Today.* `heuristic_filter.py` implements `rule_element_ratio` (Rules 4–5) and
`rule_valence` (even/odd electron). `rule_senior` is **stubbed** (`TODO: requires graph
theory`); the probabilistic element-ratio rule (6) and a principled RDBE check are not
yet there. **Partial — the spike.**
*Gap.* Complete the rule set as a **scored, referenced filter** (a graded plausibility in
[0,1] per candidate, not just a boolean pass), so it can feed the decision layer rather
than hard-cut candidates. RDBE/Senior needs a valence-graph feasibility check.

### L2 — Spectral-neighbourhood corroboration (adducts, isotopes, fragments)
*Basis.* A real compound rarely appears as a single peak. Its isotopologues, its different
adducts ($[M+H]^+$, $[M+NH_4]^+$, $[M+Na]^+$, $[M+Br]^-$ …), and its in-source fragments
**co-occur**, share a retention/elution profile, and have predictable intensity
relationships. Grouping these and checking their mutual consistency is strong corroborating
evidence and resolves many ambiguities. Tools: **CAMERA**
([Kuhl et al. 2012](https://pubs.acs.org/doi/10.1021/ac202450g)) groups isotopes/adducts by
peak-shape correlation; **Integrated Probabilistic Annotation**
([Del Carratore et al. 2019](https://pubs.acs.org/doi/10.1021/acs.analchem.9b02354)) puts
isotopes, adducts, and biochemical relations into a single Bayesian model.
*Today.* Ionization channels are enumerated independently; there is **no cross-peak
grouping or adduct-consistency corroboration**.
*Gap.* The biggest untapped source of confidence. Add an adduct/isotope grouping layer that
rewards candidates whose predicted satellite peaks (other adducts, fragments) are also
present with consistent intensities.

### L3 — Instrument & acquisition context
*Basis.* The instrument and method constrain identity. **Mass resolution** sets the mass
term's width (already in the fit score via the fitted $\sigma$). **Retention time** is a
strong orthogonal axis: predicted-vs-observed RT consistency markedly improves annotation
([Broeckling et al. 2016, *MS1 spectrum + time prediction*](https://pubs.acs.org/doi/10.1021/acs.analchem.6b02479)).
**Ionization mode and reagent chemistry** make some adducts/compounds (im)plausible.
*Today.* Resolution-aware mass is in the fit score. RT and ionization-behaviour priors are
**not** used as confidence evidence.
*Gap.* A retention-time consistency term (where RT data exists) and ionization/reagent
priors as candidate-level evidence.

### L4 — Probabilistic integration & calibration
*Basis.* Combine the independent evidence streams into a single posterior over candidates.
Two complementary tools:
- **Calibration** — map a raw score to a true probability via Platt scaling
  ([Platt 1999](https://en.wikipedia.org/wiki/Platt_scaling)) or isotonic regression. We
  already prototyped this (`calibrate_score`, the Platt curve on the demo goldens).
- **False-discovery-rate control** — estimate annotation reliability with **target–decoy**
  methods, the established approach for large-scale MS annotation
  ([Scheubert et al. 2017](https://www.nature.com/articles/s41467-017-01318-5)). Our
  near-mass *decoy* candidate generator (`tooling/score_eval/make_candidates.py`) is the
  seed of this.
*Today.* A single Platt calibration fitted on the Orbitrap demo set; a decoy generator and
an evaluation harness exist (`score_eval`).
*Gap.* **Per-instrument / per-context calibration**; a real FDR estimate; principled
combination of L1–L3 evidence (Bayesian product of likelihoods, or a learned model) rather
than the fit score alone.

### L5 — Arbitration & reporting
*Basis.* For each peak, rank the surviving candidates by combined evidence, assign the
best, and **report a confidence and a level** ([Schymanski 2014](https://pubs.acs.org/doi/10.1021/es5002105)).
Where candidates are genuinely indistinguishable, say so (report the tie, not a false
winner). This is exactly the "which of the well-fitting compositions is most likely"
problem — **peaky's purpose.**
*Today.* A heuristic ranking/selection (the spike).
*Gap.* A structured arbitration that consumes calibrated per-candidate evidence, emits a
confidence + level, and is honest about unresolved ties.

## 3. Design principles

1. **The fit score stays pure.** Competitor-awareness, chemistry, and context never get
   folded back into the measurement. They are *layers*, each separately inspectable. This
   is also what keeps the two branches/PRs cleanly separable (§0).
2. **Every layer is a likelihood or a calibrated probability**, so they compose by
   multiplication (Bayesian) and the final number is interpretable.
3. **Everything is validated against goldens.** The demo bundle + `score_eval` harness
   (ranking AUC, calibration ECE, target–decoy FDR) is the test bench for every layer.
4. **Calibration is per-instrument/context**, never a universal constant.
5. **Report levels, not just scores** — align outputs with Schymanski/MSI so confidence is
   communicated the way the field expects.
6. **Reproducibility first.** The measurement is deterministic; learned/calibrated pieces
   live in the upper layers where they can evolve without disturbing the measurement.

## 4. Phased plan

| Phase | Deliverable | Anchored in |
|---|---|---|
| **P1 — Chemistry, completed & scored** | Finish the Seven Golden Rules as a graded per-candidate plausibility (RDBE/Senior valence-graph check, DB-derived element-ratio probabilities, isotope rule), replacing the partial boolean filter. | Kind & Fiehn 2007 |
| **P2 — Candidate arbitration + FDR** | For each peak, compete candidates by fit × plausibility; calibrate to $P(\text{correct})$ per instrument; estimate FDR with the target–decoy harness. Emit a confidence. | Scheubert 2017; Platt 1999 |
| **P3 — Spectral-neighbourhood corroboration** | Adduct/isotope/in-source-fragment grouping; reward candidates corroborated by consistent companion peaks. | CAMERA 2012; IPA 2019 |
| **P4 — Context & levels** | Retention-time consistency and ionization/reagent priors as evidence; assign a Schymanski/MSI identification **level** alongside the confidence. | Broeckling 2016; Schymanski 2014 |
| **P5 — Unified probabilistic model (optional)** | Replace the hand-combined layers with one Bayesian (or learned) model over all evidence, dataset-wide. | IPA 2019; SIRIUS/ZODIAC |

**Immediate next step (P1).** Lift the chemistry filter from boolean to a graded, referenced
plausibility: implement a proper **RDBE (ring + double-bond equivalents)** and **Senior
parity / valence-graph feasibility** check (completing the stubbed `rule_senior`), plus the
DB-derived element-ratio probabilities (Rule 6). Deliverable: a per-candidate
`plausibility ∈ [0,1]` with unit tests, measured on the decoy harness (does it rank true
formulas above implausible mass-degenerate ones?). This is the smallest, fully
self-contained step that turns the spike into the first real evidence layer — and it needs
no backend or DB, only `mascope_tools` + tests.

### P1 progress

- **`rule_senior` implemented** (RDBE ≥ 0 + Senior connectivity), replacing the stub, with
  unit tests (`test_rule_senior.py`). It is conservative and **fails open**: only
  over-saturated (negative-RDBE, impossible-for-any-structure) and disconnectable formulas
  are rejected; **odd-electron radicals pass** (they can be genuine in APCI/APPI), and any
  element outside the standard valence table passes. Still **boolean** for now; the move to a
  graded `plausibility ∈ [0,1]` and the DB element-ratio probabilities (Rule 6) are the
  remaining P1 work.
- **Validated against all 92 demo target compounds** (confirmed they are genuine
  `target_compound.target_compound_formula` *neutral* formulas — ions are built `compound +
  ionization`, e.g. `C10H15O5` + `+H+` → `C10H16O5+`). After the radical fail-open, the rule
  flags exactly **1**: `C6H17NO4` (17 H on a C6NO4 skeleton; max is 15 — impossible for any
  neutral structure), almost certainly a data error.
- **Data-quality finding for later chemical review** (`analyze carefully afterwards`): four
  demo compounds are **odd-electron radicals as neutrals** — `C9H15O6`, `C10H15O5`,
  `C10H17O7` (odd H, no N) and `Br` (a lone halogen, the bromide reagent). These now *pass*
  the rule (fail-open), but it is worth confirming whether they are legitimate radical
  species or off-by-one-H / reagent-representation artefacts in the test data.

## 5. References

- Kind, T.; Fiehn, O. *Mass accuracy is insufficient even at less than 1 ppm.* BMC
  Bioinformatics 2006, 7:234.
  [link](https://bmcbioinformatics.biomedcentral.com/articles/10.1186/1471-2105-7-234)
- Kind, T.; Fiehn, O. *Seven Golden Rules…* BMC Bioinformatics 2007, 8:105.
  [link](https://bmcbioinformatics.biomedcentral.com/articles/10.1186/1471-2105-8-105)
- Böcker, S. et al. *SIRIUS: decomposing isotope patterns…* Bioinformatics 2009,
  25(2):218–224. [link](https://academic.oup.com/bioinformatics/article/25/2/218/218950)
- Dührkop, K. et al. *SIRIUS 4…* Nature Methods 2019, 16:299–302.
  [link](https://www.nature.com/articles/s41592-019-0344-8)
- Kuhl, C. et al. *CAMERA: LC-MS peak annotation and identification.* Anal. Chem. 2012,
  84(1):283–289. [link](https://pubs.acs.org/doi/10.1021/ac202450g)
- Del Carratore, F.; Schmidt, K.; Vinaixa, M. et al. *Integrated Probabilistic Annotation
  (IPA): a Bayesian-based annotation method… integrating biochemical connections, isotope
  patterns and adduct relationships.* Anal. Chem. 2019, 91(20):12799–12807.
  [link](https://pubs.acs.org/doi/10.1021/acs.analchem.9b02354)
- Broeckling, C. D. et al. *Enabling efficient and confident annotation of LC-MS
  metabolomics data through MS1 spectrum and time prediction.* Anal. Chem. 2016,
  88(18):9226–9234. [link](https://pubs.acs.org/doi/10.1021/acs.analchem.6b02479)
- Scheubert, K. et al. *Significance estimation for large-scale metabolomics annotations by
  spectral matching.* Nature Communications 2017, 8:1494.
  [link](https://www.nature.com/articles/s41467-017-01318-5)
- Schymanski, E. L. et al. *Identifying small molecules via HRMS: communicating
  confidence.* Environ. Sci. Technol. 2014, 48:2097–2098.
  [link](https://pubs.acs.org/doi/10.1021/es5002105)
- Sumner, L. W. et al. *Proposed minimum reporting standards for chemical analysis (MSI).*
  Metabolomics 2007, 3:211–221. [link](https://doi.org/10.1007/s11306-007-0082-2)
- Platt, J. *Probabilistic outputs for SVMs and comparisons to regularized likelihood
  methods.* Advances in Large Margin Classifiers, 1999.
  [link](https://en.wikipedia.org/wiki/Platt_scaling)
