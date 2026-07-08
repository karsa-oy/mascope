# Verification capture in the UI (V1) — frontend contract

*Backend V1 of the verification → calibration loop is on the epic branch: a user confirms/rejects
an identification, and the verdict is stored as a labelled record (with a score snapshot) that will
later refit the confidence calibration. This is the frontend contract for the capture control.
Design rationale + the guardrails: [`verification_calibration_loop.md`](verification_calibration_loop.md).
Scope is deliberately small — capture honest labels, nothing else. No calibration refit in the UI
(that's V2).*

## What to build

A **minimal** control on a peak assignment in the inspector
([`PanePeakAssign.vue`](../../server/frontend/src/lib/panes/PanePeakAssign/PanePeakAssign.vue)):

- **Confirm / Reject / Unsure** (make Reject exactly as prominent as Confirm — rejections are
  first-class calibration negatives).
- An **evidence-level** dropdown (see enum below). **Required when confirming** (the API rejects a
  `confirmed` verdict with no evidence level); optional for reject/unsure.
- An optional **note** (free text).
- A **verdict badge** on the assignment showing its current verdict (+ evidence level) once set.
- A ledger filter: **verified / rejected / unverified**.

Not in V1: the structured isotope-by-isotope checklist, and any "recalibrate" action.

## API (epic branch, under `/api/peak-assignments`)

| Method | Path | Body / returns |
|---|---|---|
| `POST` | `/sample/{sample_item_id}/verify` | body below → `201` `AssignmentVerificationsResponse` (the created record in `data[0]`). Requires **editor**. |
| `GET` | `/sample/{sample_item_id}/verifications` | `AssignmentVerificationsResponse` — all verdicts for the sample, newest first. Requires guest. |

**POST body:**

```json
{ "peak_assignment_id": "…", "verdict": "confirmed",
  "evidence_level": "reference_standard", "note": "optional" }
```

- `verdict`: `confirmed` | `rejected` | `unsure`.
- `evidence_level` (required iff `confirmed`): `reference_standard` | `msms` | `orthogonal` |
  `pattern` | `visual`.

**Record shape** (`AssignmentVerificationRecord`):

```
assignment_verification_id · sample_item_id · peak_assignment_id · peak_assignment_run_id
sample_peak_id · assigned_formula · ionization_mechanism_id
verdict · evidence_level · note
fit_score · evidence · p_correct   (snapshot at verification time)
verified_by · verified_utc
```

## Evidence levels (labels + meaning)

Ordered strongest → weakest; surface the meaning, not just the key:

| key | label | meaning |
|---|---|---|
| `reference_standard` | Reference standard | authentic standard — RT + mass match (strongest) |
| `msms` | MS/MS | MS/MS or diagnostic fragments |
| `orthogonal` | Orthogonal | RT or other orthogonal evidence |
| `pattern` | Isotope/adduct pattern | in-spectrum isotope + adduct corroboration only |
| `visual` | Visual | manual review, no independent evidence (weakest) |

## Deriving the current verdict

The GET returns the **append-only history**. The current verdict for an assignment is the
**latest by `verified_utc`** among records matching its stable identity —
`sample_peak_id` + `assigned_formula` + `ionization_mechanism_id` (not `peak_assignment_id`, which
changes on every re-run). Join the verifications store to the assignments by that identity, take the
newest per group, and show it as the badge / drive the ledger filter.

## Two UX guardrails (from the design)

1. **Don't anchor the judgment on `p_correct`.** During verification, keep the model's probability
   de-emphasised (or hidden) so the user judges the *data* — otherwise the labels just echo the model
   and the eventual calibration learns nothing. Showing fit / isotopes / adducts is fine; leading with
   "Mascope says 92%" is not.
2. **Reject is not a second-class action.** Equal prominence to Confirm.

## TL;DR

- POST `/sample/{id}/verify` with `{peak_assignment_id, verdict, evidence_level?, note?}` (editor).
- GET `/sample/{id}/verifications`; current verdict = latest by `verified_utc` per
  `sample_peak_id`+formula+adduct.
- Confirm requires an evidence level; make Reject equally easy; don't lead with `p_correct`.
