# The Match Fit Score (v2)

*Reference for `mascope_tools.composition.heuristic_filter.score_pattern_v2`
(`SCORE_VERSION = 2`).*

## 1. What it is — and what it is not

The match score answers exactly one question:

> **How well does the observed data fit the predicted spectrum of *this* assignment?**

It is a **fit-quality measurement** on $[0, 1]$ (1.0 = perfect fit), computed per ion
from its isotopologue peaks. It is deliberately:

- **competitor-blind** — it knows nothing about alternative formulas that might explain
  the same peak;
- **not a probability of correctness** — mass alone cannot prove a composition
  ([Kind & Fiehn 2006](https://bmcbioinformatics.biomedcentral.com/articles/10.1186/1471-2105-7-234)),
  so "is this the *right* formula among the ones that fit?" is a separate
  **identification-confidence** layer (a distinct workstream that builds on this score);
- **deterministic and reproducible** — the same spectrum always yields the same score,
  with no dependence on a trained/calibrated model.

This separation is the central design decision: the score is the *pure-math measurement*;
chemistry, instrument context, and candidate arbitration are layered on top and never
folded back into it.

## 2. Scientific rationale

High mass accuracy alone is insufficient to determine elemental composition: even at
<1 ppm the number of formulas within tolerance grows quickly with mass and heteroatom
count, and a measurement at 3 ppm **plus** 2 % isotope-abundance accuracy outperforms a
hypothetical 0.1 ppm instrument with no isotope information
([Kind & Fiehn 2006](https://bmcbioinformatics.biomedcentral.com/articles/10.1186/1471-2105-7-234)).
The fit score therefore scores the **whole isotope pattern**, not just the monoisotopic
mass: each predicted isotopologue contributes mass *and* relative-intensity evidence.

The construction follows the probabilistic isotope-pattern matching of **SIRIUS**
([Böcker et al. 2009](https://academic.oup.com/bioinformatics/article/25/2/218/218950);
[Dührkop et al. 2019](https://www.nature.com/articles/s41592-019-0344-8)), where mass
deviations are modelled as normal distributions and the pattern is scored as a product of
per-peak likelihoods. v2 adapts this to centroided industrial spectra by adding
detection-limit awareness (real signal-to-noise) and resolution-aware mass widths so the
same score is valid for both Orbitrap and TOF instruments.

### Why v2 replaced v1

The legacy score was a fixed linear blend — $0.6\cdot\text{mass} + 0.2\cdot\text{cosine}
+ 0.2\cdot\text{intensity}$ — averaged over *matched* peaks only, with a hard 5 ppm mass
window. It (a) ignored predicted peaks that should have been visible but were not, (b)
judged intensities without reference to noise, and (c) used an instrument-agnostic mass
window. v2 fixes all three. On the demo golden set, ranking ROC-AUC improves 0.876→0.890
and held-out calibration ECE 0.020→0.0069 (see
[`tooling/score_eval/DESIGN.md`](../../../tooling/score_eval/DESIGN.md)).

## 3. The model

Inputs, per predicted isotopologue $i$ (index $0$ = the monoisotopic / base peak, ordered
by descending predicted abundance):

| symbol | meaning |
|---|---|
| $p_i$ | predicted relative abundance (base-normalised, $p_0 = 1$) |
| $e_i$ | observed mass error in ppm (offset-centred: the fitted $\mu$ is subtracted) |
| $o_i$ | observed intensity ($o_i = 0$ if no peak matched) |
| $s_i$ | observed signal-to-noise of the matched peak |
| $\sigma$ | instrument mass-error std in ppm (`sigma_ppm`) |

**Guard.** If the monoisotopic peak is absent ($o_0 \le 0$) the score is $0$ — without the
base peak there is no assignment.

### 3.1 Mass likelihood (Gaussian, resolution-aware)

$$ L^{\text{mass}}_i = \exp\!\left(-\tfrac{1}{2}\left(\frac{e_i}{\sigma}\right)^2\right) $$

A Gaussian in ppm, as in SIRIUS. The width $\sigma$ is the **instrument's measured mass
accuracy**, fitted per sample from the matched peaks' mass errors (robust median/MAD) and
combined in quadrature with a small prediction term. This makes the score
**resolution-fair**: a 2 ppm error is near-perfect on a ~10 ppm TOF but poor on a ~1 ppm
Orbitrap, and $\sigma$ scales accordingly. The fallback `FALLBACK_SIGMA_PPM = 2.0` is
Orbitrap-appropriate and *wrong* for TOF — always pass the fitted $\sigma$.

### 3.2 Intensity likelihood (noise-propagated tolerance)

Let $r_i = o_i / o_0$ be the observed abundance relative to the base peak. The tolerance on
$r_i$ comes from **propagating counting noise** through the ratio (the relative error of a
quotient is the quadrature sum of the relative errors, and $\delta o / o \approx 1/\text{SNR}$):

$$ \sigma^{\text{rel}}_i = \max\!\left( r_i\sqrt{\tfrac{1}{s_i^2} + \tfrac{1}{s_0^2}},\; 0.05\,p_i,\; 10^{-3}\right), \qquad
L^{\text{int}}_i = \exp\!\left(-\tfrac{1}{2}\left(\frac{r_i - p_i}{\sigma^{\text{rel}}_i}\right)^2\right) $$

So a weak, noisy isotopologue is judged loosely (its ratio is uncertain) while a strong,
clean one is judged tightly — rather than a single global intensity tolerance. The floors
($5\%$ of predicted abundance, and $10^{-3}$) prevent over-confident penalties.

The base peak carries only mass evidence ($L_0 = L^{\text{mass}}_0$, since $r_0 \equiv 1$);
every other **matched** peak contributes $L_i = L^{\text{mass}}_i \cdot L^{\text{int}}_i$.

### 3.3 Detectability gate (censoring at the detection limit)

A predicted peak that is **absent** ($o_i = 0$) is only evidence *against* the assignment
if it should have been seen. Its expected SNR is $p_i \cdot s_0$ (its abundance relative to
the base peak, times the base peak's SNR), so:

- **detectable but absent** ($p_i\, s_0 \ge k_{\text{detect}}$): contributes a fixed
  penalty $L_i = \text{miss\_penalty}$ — the assignment predicts a visible peak that is not
  there;
- **undetectable** ($p_i\, s_0 < k_{\text{detect}}$): **excluded** from the score — its
  absence is expected (below noise) and carries no information.

This is a censored-data treatment: missing low-abundance isotopologues do not punish
genuine low-intensity ions, but a missing $^{81}$Br twin of a bromine ion does. Defaults
$k_{\text{detect}} = 3$, $\text{miss\_penalty} = 0.3$.

### 3.4 Satellites

Ringing/satellite artefacts near intense peaks are **not** real matches; the caller flags
them and they are treated as absent (so the detectability gate applies). See
`ion_score_v2` in the backend adapter.

### 3.5 Aggregation (abundance-weighted geometric mean)

The included per-isotopologue likelihoods are combined as a **predicted-abundance-weighted
geometric mean**:

$$ \text{score} = \exp\!\left(\frac{\sum_i w_i \ln L_i}{\sum_i w_i}\right), \qquad w_i = p_i $$

The geometric mean is the natural combination of independent likelihoods (it is
$\exp$ of the mean log-likelihood, i.e. a normalised joint likelihood), and the abundance
weighting means the dominant isotopologues drive the score while trace peaks contribute
proportionally less. The result is in $[0,1]$, equals $1$ only for a flawless fit, and is
**monotone in isotopic corroboration** — more clean, in-pattern peaks → higher score.

## 4. Parameters

| parameter | default | role |
|---|---|---|
| `sigma_ppm` | per-sample fitted (fallback `2.0`) | mass-term width; the instrument-resolution lever |
| `k_detect` | `3.0` | expected-SNR threshold above which an absent peak is penalised |
| `miss_penalty` | `0.3` | likelihood assigned to a detectable-but-absent peak |
| `PRED_SIGMA_PPM` | `0.5` (backend adapter) | prediction/centroiding term added to $\sigma$ in quadrature |

## 5. Properties (validated on the demo)

- **Reproducible / instrument-fair:** deterministic; resolution handled by the fitted
  $\sigma$. Live demo fit-quality: median **0.92**, max **1.0**.
- **Monotone in corroboration:** median score rises with the number of clean, in-tolerance
  isotopologues (1 peak ≈ 0.3 → full envelope ≈ 0.95). v1 gave ~0.95 regardless.
- **Correctly demotes weak matches:** 86 % of sub-0.5 ions on the demo have 0–1
  in-tolerance isotopologues — absent/trace assignments that v1 inflated on mass alone.

## 6. Limitations

- **Geometric-mean harshness (rare):** one badly-fitting high-abundance peak can dominate.
  On the demo this affects ~1 % of ions; revisit the aggregation (e.g. a soft floor or a
  robust mean) if it proves material.
- **Depends on isotopologue matching completeness:** a *missed* match looks like a missing
  predicted peak, so the score is only as good as the upstream peak matching.
- **Single-ion:** it scores one ion's isotope envelope; cross-peak corroboration (adducts,
  in-source fragments) is the confidence layer's job, not the score's.
- **Not a probability:** pairing with `calibrate_score` (Platt) yields a single-candidate
  $P(\text{correct})$, but that belongs to the identification-confidence layer (a separate
  workstream), not the fit score.

## References

- Kind, T.; Fiehn, O. *Metabolomic database annotations via query of elemental
  compositions: mass accuracy is insufficient even at less than 1 ppm.* **BMC
  Bioinformatics** 2006, 7:234.
  [link](https://bmcbioinformatics.biomedcentral.com/articles/10.1186/1471-2105-7-234)
- Kind, T.; Fiehn, O. *Seven Golden Rules for heuristic filtering of molecular formulas
  obtained by accurate mass spectrometry.* **BMC Bioinformatics** 2007, 8:105.
  [link](https://bmcbioinformatics.biomedcentral.com/articles/10.1186/1471-2105-8-105)
- Böcker, S.; Letzel, M. C.; Lipták, Z.; Pervukhin, A. *SIRIUS: decomposing isotope
  patterns for metabolite identification.* **Bioinformatics** 2009, 25(2):218–224.
  [link](https://academic.oup.com/bioinformatics/article/25/2/218/218950)
- Dührkop, K. et al. *SIRIUS 4: a rapid tool for turning tandem mass spectra into
  metabolite structure information.* **Nature Methods** 2019, 16:299–302.
  [link](https://www.nature.com/articles/s41592-019-0344-8)
