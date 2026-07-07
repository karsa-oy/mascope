# Peak-Centric Assignment — Frontend Design & Implementation Plan

*The UI side of the peak-centric paradigm ([`peak_assignment_paradigm.md`](peak_assignment_paradigm.md)).
The backend inverts the unit of result from target to observed peak; this document is how the
Vue/PrimeVue frontend consumes that. It is weighted toward the technical wiring — stores, API,
socket/notification, join keys — and keeps net-new UI deliberately small.*

## 0. Decisions settled

| Question | Decision |
|---|---|
| Match tab (spectrum + isotope timeseries) | **Keep it, rename to "Fit view".** It is the visual verification that a signal fit is good. |
| Match **browser / ion table** (bottom-left) | Peak assignments go **here**. Coexist with the target/ion tables at first; **aim to retire** the `match_ion` table. |
| Tier band recalibration | Real, but **backend work** (`tier_for_score`); the UI just renders whatever tier the API returns. |
| `match_score` naming | UI labels say **"fit"** everywhere new. The `PeakAssignment` surface already carries `fit_score`. |

## 1. The backend contract (what we consume)

Three endpoints, all under `/api/peak-assignments` (see
[`routes.py`](../../server/backend/src/mascope_backend/api/new/peak_assignments/routes.py)):

| Method | Path | Returns | Notes |
|---|---|---|---|
| `GET` | `/sample/{sample_item_id}` | `{ run, data: PeakAssignment[] }` | Query: `peak_assignment_run_id?`, `tier?`, `role?`, `source?`. No run id ⇒ **latest completed** run. |
| `GET` | `/sample/{sample_item_id}/runs` | `{ data: PeakAssignmentRun[] }` | Newest first. |
| `POST` | `/sample/{sample_item_id}/assign` | `202 { message, process_id }` | Body `{ config?: PeakAssignmentConfig }`. Requires `editor`. |

**Record shape** (`PeakAssignmentRecord`, one row per observed peak):

```
peak_assignment_id · peak_assignment_run_id · sample_item_id
sample_peak_id · sample_peak_mz · sample_peak_intensity · sample_peak_tof
role            M0 | iso_child | reagent | artifact | unassigned
tier            identified | candidate | below_assignability | unassigned
source          database | untargeted | null
assigned_formula · ion_formula · ionization_mechanism_id · isotope_label
fit_score · mz_error_ppm · abundance_error
target_compound_id · target_ion_id        (nullable — set when the winner came from the library)
owner_peak_assignment_id                   (an iso_child points at its M0)
alternatives (JSON list) · provenance (JSON)
```

### 1.1 Two facts that drive the wiring

1. **Join key.** The peak list (`GET /samples/{id}/peaks`) returns `peak_id`; the engine stringifies
   the same column into `sample_peak_id` (`_load_sample_peaks`,
   [`service.py`](../../server/backend/src/mascope_backend/api/new/peak_assignments/service.py)).
   So the peak↔assignment join is **`String(peak.peak_id) === assignment.sample_peak_id`**. Coerce to
   string on both sides.

2. **Completion is a *notification*, not a record socket event.** `rematch_sample` emits a
   `match_reload` socket event that the `useData` events framework auto-handles. The assignment task
   does **not** — it only sends `user_notification` of `type: "assign_sample_peaks"` (a `pending`
   progress stream 0.1→1.0, then a terminal `success`/`error`), whose `data` carries
   `sample_item_id` and `peak_assignment_run_id`. So a run store cannot rely on `*_reload`; it must
   either watch that notification or we add a socket event (see §2.3, **one backend ask**).

## 2. New Pinia stores

Two modules under `src/stores/data/modules/peakAssignment/`, mirroring `modules/match/`. Both use the
existing [`useData`](../../server/frontend/src/lib/store/data.js) composable (deps-driven reload,
selection, socket CRUD auto-registration).

### 2.1 `usePeakAssignmentRun` — the run list + selector

```js
// modules/peakAssignment/run.js
export const usePeakAssignmentRun = defineStore('app.data.peakAssignment.run', () => {
  const name = 'peak_assignment_run'
  const key = 'peak_assignment_run_id'

  const data = useData(
    name,
    ({ sample_item_id }) =>
      sample_item_id
        ? api.http.get(`/peak-assignments/sample/${sample_item_id}/runs`, {
            use: 'read', type: 'load_peak_assignment_runs'
          }).then((r) => r.data)     // handler unwraps to the array
        : [],
    {
      key,
      deps: () => ({ sample_item_id: useSample().focusedId }),
      selection: true                // focused run == the run being viewed
    }
  )

  // default focus = latest COMPLETED run (list is newest-first)
  const latestCompleted = computed(() =>
    data.list.value.find((run) => run.status === 'completed') ?? null)

  // launch a run; returns process_id, completion arrives via notification (§2.3)
  const assign = (sampleItemId, config) =>
    api.http.post(`/peak-assignments/sample/${sampleItemId}/assign`, { config },
      { use: 'read', type: 'assign_sample_peaks' })

  return { ...data, latestCompleted, assign }
})
```

### 2.2 `usePeakAssignment` — the ledger for the focused sample + selected run

**Handler caveat.** The shared `read` handler returns `response.data.data` — i.e. it unwraps to the
body's `data` field and **drops the sibling `run`** from the `{ run, data }` envelope
([`handlers.js`](../../server/frontend/src/api/handlers.js)). So the assignment fetch yields only the
array; **run metadata comes from the run store** (`usePeakAssignmentRun().focused`, which already holds
each run's full `to_dict()`), not the envelope. To keep that unambiguous, the app **explicitly focuses
`latestCompleted`** once runs load (a one-line watcher in the Assignments browser), so
`peak_assignment_run_id` is never `null` at fetch time and the viewed run is always the focused one.

```js
// modules/peakAssignment/assignment.js
export const usePeakAssignment = defineStore('app.data.peakAssignment', () => {
  const name = 'peak_assignment'
  const key = 'sample_peak_id'       // unique within a run; the peak-join key

  const data = useData(
    name,
    ({ sample_item_id, peak_assignment_run_id }) => {
      if (!sample_item_id || !peak_assignment_run_id) return []
      return api.http.get(`/peak-assignments/sample/${sample_item_id}`, {
        params: { peak_assignment_run_id },
        use: 'read', type: 'load_peak_assignments'   // → assignments array
      })
    },
    {
      key,
      deps: () => ({
        sample_item_id: useSample().focusedId,
        peak_assignment_run_id: usePeakAssignmentRun().focusedId ?? null
      }),
      selection: true
    }
  )

  // run metadata for the current view (status, config, timestamps)
  const run = computed(() => usePeakAssignmentRun().focused)

  // peak-join map + tier histogram: consumed by the ledger AND the spectrum
  const byPeakId = computed(() => {
    const m = new Map()
    for (const a of data.list.value) m.set(String(a.sample_peak_id), a)
    return m
  })
  const tierCounts = computed(() => {
    const c = { identified: 0, candidate: 0, below_assignability: 0, unassigned: 0, reagent: 0 }
    for (const a of data.list.value) {
      if (a.role === 'reagent' || a.role === 'artifact') c.reagent++
      else c[a.tier] = (c[a.tier] ?? 0) + 1
    }
    return c
  })

  return { ...data, run, byPeakId, tierCounts }
})
```

Register both in [`stores/data/index.js`](../../server/frontend/src/stores/data/index.js):

```js
peakAssignment: {
  run: usePeakAssignmentRun(),
  ...usePeakAssignment()          // spread so app.data.peakAssignment.list / byPeakId / run
}
```

**Filtering** (tier/role/source) is **client-side** off `data.list` — the full ledger is already in
memory, so filter chips are instant. The server query params exist for later pagination only.

### 2.3 Run-completion refresh — pick one

- **Minimal (no backend change).** A small composable `usePeakAssignmentProgress()` mounted in the
  Assignments browser registers `app.ui.notification.on('assign_sample_peaks', ...)`; on a terminal
  `success` whose `data.sample_item_id === sample.focusedId`, it calls `run.load()` then selects the
  new `peak_assignment_run_id`, which cascades into the assignment store via deps. (The notification
  store's `on()` self-unmounts via `onBeforeUnmount`, so it must live in a component, not a store.)
- **Idiomatic (one backend ask, recommended).** Emit a `peak_assignment_run` socket event
  (`created`/`updated`) — or a `peak_assignment_reload` cross-store event — when a run finalizes, the
  way `rematch_sample` emits `match_reload`. Then `usePeakAssignmentRun` handles it automatically via
  the `useData` events framework (`events: ['peak_assignment_reload']`), no component watcher. This is
  the same pattern the match stores already use and is the clean long-term answer.

## 3. Component changes (kept small)

Layout is unchanged. Most work is reframing three existing panes + one new tag + one config dialog.

| File | Change | Effort |
|---|---|---|
| [`PaneBrowserPeak.vue`](../../server/frontend/src/lib/panes/PaneBrowserPeak/PaneBrowserPeak.vue) | The **ledger**. Replace the header ratio with `tierCounts`; add a **formula + tier + source + fit** column set read from `byPeakId.get(String(data.peak_id))`; keep the legacy `match[]` buttons behind the coexistence flag. | M |
| [`PanePeakAssign.vue`](../../server/frontend/src/lib/panes/PanePeakAssign/PanePeakAssign.vue) | The **inspector**. When the focused peak has an assignment, render committed winner + evidence + `alternatives` + known-compound; demote the existing on-demand `/cheminfo/mz/match` search to a **"Re-search"** action. (The whole current file becomes the fallback path.) | M |
| [`ChartSampleSpectrum/data.js`](../../server/frontend/src/lib/charts/ChartSampleSpectrum/data.js) | **Annotated spectrum.** Split the single grey `Peak` trace into one trace per tier (color from `byPeakId`), plus a reagent/artifact trace. Focus/preview traces unchanged. Legend = trace names. | S |
| [`PaneBrowserMatch.vue`](../../server/frontend/src/lib/panes/PaneBrowserMatch/PaneBrowserMatch.vue) | Add an **"Assignments"** tab beside the existing Targets/collections view: run selector + `tierCounts` histogram + a per-peak list backed by `usePeakAssignment`. Row click ⇒ `app.data.peak.focused = <matching peak>` (drives the Sample tab). Existing `MatchIonTable` stays under a "Targets" tab. | M |
| `BaseTierTag.vue` **(new)** | 4-tier chip + `fit_score` + role icon. One shared component; keep `BaseMatchTag` for the legacy targeted view. | S |
| Run-config dialog **(new)** | `run_untargeted`, `mz_precision_ppm`, `formula_ranges`, `max_untargeted_peaks`, `peak_intensity_threshold`, `max_alternatives`. Reuse `SidebarMatchParams` patterns; submit ⇒ `run.assign(...)`. | S |
| `Dashboard.vue` tab label | `"Match"` → `"Fit"` (see §4). Help text updated. | XS |

The **inspector reads from the focused peak**, not its own selection: `app.data.peakAssignment.byPeakId
.get(String(app.data.peak.focused?.peak_id))`. No new selection wiring needed for the common path.

## 4. The Fit view rename & the untargeted-visualization gap

Renaming the tab is cosmetic. The **functional** issue: the Fit view
([`visualized.js`](../../server/frontend/src/stores/data/modules/match/visualized.js)) is driven
entirely by `target_ion_id` + `target_collection_id` (`/match/aggregate/.../ion`,
`/visualization/ion_focus`). That works for **database** assignments (they carry `target_ion_id`) but
**untargeted winners have no `target_ion_id`** — so "verify this fit" cannot open the Fit view for a
Stage B assignment as things stand.

Options (a backend/product call, flag for the epic):
- **A. Composition-driven Fit view** — a visualization endpoint that renders the isotope envelope +
  per-isotopologue timeseries from a *formula + ionization mechanism*, not a `target_ion_id`. Cleanest;
  makes the Fit view work for every assignment.
- **B. Ephemeral/persisted target ion** — Stage B commits a lightweight `TargetIon` (or a scratch one
  on demand) so the existing Fit path just works. Reuses everything but muddies the target tables.

Until one lands, the Assignments browser should only offer "Verify fit" on rows where
`target_ion_id != null`, and show the inspector's isotope evidence for the rest.

## 5. Labels

- New surfaces say **"Fit"** / **"Fit score"**; the tag renders `fit_score`.
- `BaseTierTag` replaces the 0/1/2 severity of `BaseMatchTag` with the 4 tiers; `BaseMatchTag` stays
  only where the legacy `match_category` is still shown (targeted view during coexistence).

## 6. Phased checklist

- **A — Read the run (ships first, GET-only).** `usePeakAssignmentRun` + `usePeakAssignment` + index
  registration; `BaseTierTag`; ledger columns in `PaneBrowserPeak`; spectrum coloring. No writes, no
  new science. Depends only on endpoints already on the epic branch.
- **B — Launch & watch.** Run-config dialog + `run.assign()`; completion refresh (§2.3 — do the
  backend socket event here); run selector in the Assignments browser.
- **C — Inspect & act.** Inspector `alternatives` + commit-alternative + add-to-target-list; "Re-search"
  fallback. Needs the untargeted-visualization decision (§4) for "Verify fit".
- **D — Retire the match_ion table.** Fold the Targets view into a `source=database` /
  `target_compound_id != null` filter over the ledger; remove `MatchIonTable` once parity is reached.
- **E — Batch level.** Batch-overview coloring by tier; GKA / Van Krevelen (backend Phase 4).

## 7. Backend asks (small, for a clean frontend)

1. **A run-finalized socket event** (`peak_assignment_run` created/updated, or `peak_assignment_reload`),
   mirroring `match_reload`, so run refresh is idiomatic (§2.3).
2. **A composition-driven Fit visualization** (or ephemeral target ion) so the Fit view works for
   untargeted assignments (§4).
3. None for the read path: the `read` handler's `data.data` unwrap means we take run metadata from the
   runs endpoint (via the run store) rather than the `{run, data}` envelope — no backend change needed,
   but if we later want the envelope's `run` in one call, add a dedicated handler rather than reusing
   `read`.
