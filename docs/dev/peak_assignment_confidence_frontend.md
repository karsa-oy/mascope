# Surfacing assignment confidence in the UI

*A short guide for the frontend work on the peak-centric assignment views. The backend now
produces four related confidence quantities per peak; the current UI shows two of them. This
explains what each one is, where it lives on the record, and how to surface the probability and
(soon) the adduct-corroboration signal honestly. Backend science lives in
[`assignment_confidence.md`](assignment_confidence.md); this is the consumer's-eye view. See also
the wiring plan in [`peak_assignment_frontend.md`](peak_assignment_frontend.md).*

## The four quantities (and where they live)

Every `PeakAssignmentRecord` (one per observed peak) carries the confidence story in these fields.
Two are top-level; the rest ride inside the `provenance` JSON blob.

| Quantity | What it means | Range | Field path | Shown today |
|---|---|---|---|---|
| **fit_score** | How well the *measurement* matches this ion — mass error + intensity + isotope envelope. Pure signal. | 0–1 | `fit_score` (top-level) | ✅ Fit column / tier tag |
| **plausibility** | Chemistry sanity of the formula — the Seven Golden Rules (Kind & Fiehn 2007). Independent of the measurement. | 0–1 | `provenance.plausibility` | ✅ Plausibility column |
| **evidence** | `fit x plausibility` — the score arbitration ranks candidates by. Rarely worth showing on its own. | 0–1 | `provenance.evidence` | ❌ |
| **p_correct** | **Calibrated probability the assignment is correct.** `evidence` mapped through a Platt curve to a real probability. | 0–1 | `provenance.p_correct` | ❌ — *this is the "probability"* |

So the answer to "do we have the probability?" is **yes** — it is `provenance.p_correct`, already
computed and stored. The UI just isn't reading it yet. Example provenance blob from a database
assignment on the demo:

```json
{
  "evidence": 0.9077,
  "p_correct": 0.8636,
  "calibrated": true,
  "calibration": { "instrument": "orbi", "provisional": true,
                   "source": "demo goldens (Br/Ur, preliminary)" },
  "plausibility": 1.0,
  "confidence": 1.0,
  "is_tie": false
}
```

## Two honest caveats `p_correct` demands

`p_correct` is trickier to display than fit/plausibility, which are always present. Handle these or
it will mislead:

1. **It is database-stage + calibrated-instrument only.** Stage A (`source: "database"`) on an
   instrument with a calibration curve gets a number; **untargeted (`source: "untargeted"`, Stage B)
   and uncalibrated instruments (e.g. TOF) get `p_correct: null`** — deliberately. We do not
   fabricate a probability we can't back. **Render null as "-" / "uncalibrated", never as "0%".**
   Check `provenance.calibrated === true` before showing a percentage.

2. **The current curve is provisional.** `provenance.calibration.provisional === true` means the
   Orbitrap curve was fit on our preliminary demo goldens, not a curated reference set. It is
   directionally right (ECE ~= 0.03) but should not be presented as a hardened figure. When
   `provisional`, label it — e.g. `~86% correct (provisional)` — so users don't over-trust it.

### Suggested display

- A stat like **"~86% likely correct (provisional)"** next to fit/plausibility, that
  reads `provenance.p_correct`, formats null as "uncalibrated", and appends "(provisional)" while
  `provenance.calibration.provisional` is true.
- It slots in exactly where `plausibility` does. Note the store currently returns records raw
  (no provenance flattening); read `record.provenance?.p_correct` directly, or add a thin flatten in
  `usePeakAssignment` mirroring how you'd expose `plausibility`.

## Alternatives now carry plausibility too

As of the latest engine change, each entry in `alternatives` (the runner-ups) carries its own
`plausibility` (database runner-ups also carry `fit_score` + `mz_error_ppm`; untargeted runner-ups
are formula-only + plausibility). So the inspector can rank and tooltip competitors by a real stat,
consistently across both stages. `p_correct` is **not** on alternatives — it is a
winner-only, arbitrated quantity.

## Coming soon: adduct corroboration

A real compound usually appears through several adducts (`[M+H]+`, `[M+NH4]+`, `[M+Na]+`,
`[M+Br]-` ...). Their co-occurrence is independent corroborating evidence (the basis of CAMERA /
IPA) and a strong indicator of a correct formula. The signal is already computed per compound
(`corroboration = 1 - 2^-(n_adducts-1)`: 0 for a lone adduct, 0.5/0.75/0.875 for 2/3/4).

**How it will reach you:** we are measuring the empirical lift on the golden set and folding it into
`p_correct` as a Bayesian odds update, so **you should not need a new formula** — `p_correct` will
already include it, and a `provenance.corroboration` / `n_adducts` field will be exposed for display.
Until that lands, if you want to surface it early, show it as a **separate badge**
("supported by 3 adducts") rather than mixing it into the number — that stays honest and avoids
double-counting.

## TL;DR for the implementer

- The probability exists: **`provenance.p_correct`**. Wire it in.
- Gate on `provenance.calibrated`; show null rows as "uncalibrated", not 0%.
- Flag provisional via `provenance.calibration.provisional`.
- Alternatives now have `plausibility`; use it for competitor ranking.
- Don't hand-roll corroboration math — it will arrive baked into `p_correct` plus a display field.
