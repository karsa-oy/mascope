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
      selection: true,               // focused run == the run being viewed
      events: ['peak_assignment_reload']   // backend emits on run finalize (B1)
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

Register both in [`stores/data/index.js`](../../server/frontend/src/stores/data/index.js) as a
namespace (nested, **not** spread — spreading a Pinia store snapshots its refs and breaks reactivity):

```js
peakAssignment: {
  run: usePeakAssignmentRun(),   // app.data.peakAssignment.run.{list,focused,assign,latestCompleted}
  peak: usePeakAssignment()      // app.data.peakAssignment.peak.{list,byPeakId,forPeak,tierCounts,run}
}
```

The selection state of both stores is registered in
[`stores/data/filter.js`](../../server/frontend/src/stores/data/filter.js)
(`peak_assignment_run`, `peak_assignment`) so `useSelection` binds to the shared filter store
rather than a local fallback ref.

**Filtering** (tier/role/source) is **client-side** off `data.list` — the full ledger is already in
memory, so filter chips are instant. The server query params exist for later pagination only.

### 2.3 Run-completion refresh — `peak_assignment_reload` event (decided)

The backend emits a **`peak_assignment_reload`** cross-store event when a run finalizes, mirroring the
way `rematch_sample` emits `match_reload` (backend task **B1**, §7 — implemented as
`success_reload=[("peak_assignment", "sample_batch_id")]` on the `assign_sample_peaks` decorator; the
room id resolves from the returned `_notification_data.sample_batch_id`, the same room the client
already joins for match). The run store refreshes through the existing `useData` events framework with
no component-scoped notification watcher — hence `events: ['peak_assignment_reload']` in §2.1. The event name is deliberately semantic (not
`peak_assignment_run_reload`) to match the `match_reload` precedent and to let both stores subscribe if
needed.

On the event: `usePeakAssignmentRun` re-syncs its runs; the Assignments browser then **selects the
newly completed run when the user launched it this session, otherwise surfaces a "new run available"
affordance** rather than yanking the view off a run they were inspecting. Selecting a run changes
`usePeakAssignment`'s deps, which cascades the ledger reload. (The earlier notification-watch fallback
is dropped now that the event exists; the `assign_sample_peaks` progress notification is still used
purely for the progress bar via the existing `PaneProgress`.)

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

## 4. The Fit view rename & composition-driven visualization (decided)

Renaming the tab is cosmetic. The **functional** change: the Fit view
([`visualized.js`](../../server/frontend/src/stores/data/modules/match/visualized.js)) is driven
entirely by `target_ion_id` + `target_collection_id` (`/match/aggregate/.../ion`,
`/visualization/ion_focus`), which **untargeted winners don't carry**. Decision: the **Fit
visualization will accept a composition** (formula + ionization mechanism + sample), not only a
`target_ion_id` (backend task **B2**, §7). With it the Fit view works for *every* assignment and the
Assignments browser can offer "Verify fit" on any row.

Frontend consequence (task **F6**): `useMatchVisualized.set(...)` gains a composition branch —
when the focused assignment has a `target_ion_id` it takes today's path; otherwise it calls the new
composition endpoint with `assigned_formula` + `ionization_mechanism_id` from the `PeakAssignment`
row. The chart components (`ChartMatchSpectra`, `ChartMatchTimeseries`) are unchanged as long as B2
returns the same `{ match_ions, match_isotopes }` shape they consume today.

## 5. Labels

- New surfaces say **"Fit"** / **"Fit score"**; the tag renders `fit_score`.
- `BaseTierTag` replaces the 0/1/2 severity of `BaseMatchTag` with the 4 tiers; `BaseMatchTag` stays
  only where the legacy `match_category` is still shown (targeted view during coexistence).

## 6. Phased checklist

- **A — Read the run (ships first, GET-only).** `usePeakAssignmentRun` + `usePeakAssignment` + index
  registration; `BaseTierTag`; ledger columns in `PaneBrowserPeak`; spectrum coloring. No writes, no
  new science. Depends only on endpoints already on the epic branch.
- **B — Launch & watch.** Run-config dialog + `run.assign()`; completion refresh via
  `peak_assignment_reload` (§2.3); run selector in the Assignments browser.
- **C — Inspect & act.** Inspector `alternatives` + commit-alternative + add-to-target-list; "Re-search"
  fallback; "Verify fit" via the composition Fit view (§4).
- **D — Retire the match_ion table.** Fold the Targets view into a `source=database` /
  `target_compound_id != null` filter over the ledger; remove `MatchIonTable` once parity is reached.
- **E — Batch level.** Batch-overview coloring by tier; GKA / Van Krevelen (backend Phase 4).

## 7. Work distribution

### Implementation status

Landed on `design/peak-centric-frontend` (build + lint + 82 unit tests green; backend change
compile-checked, backend suite needs Postgres):

| ID | Status | Commit |
|---|---|---|
| **F1** store spine + tier tag | ✅ done | `feat(frontend): peak-assignment stores and tier tag (F1)` |
| **F2** peak ledger | ✅ done | `feat(frontend): reframe peak browser as the assignment ledger (F2)` |
| **F3** peak inspector | ✅ done | `feat(frontend): peak inspector shows the committed assignment (F3)` |
| **F4** annotated spectrum | ✅ done | `feat(frontend): color the spectrum by assignment tier (F4)` |
| **F5** assignments browser + config dialog | ✅ done | `feat(frontend): assignments browser with run selector and config dialog (F5)` |
| **F6** Fit-view rename | ✅ done (rename only) | `feat(frontend): rename the Match tab to Fit view (F6)` |
| **B1** `peak_assignment_reload` event | ✅ done | `feat(peak-assignments): emit peak_assignment_reload on run finalize (B1)` |
| **F6** composition Fit wiring | ⏳ blocked on **B2** | — |
| **B2** composition Fit visualization | ⏳ not started (needs a live stack) | — |

Not yet verified end-to-end against a running demo stack (the reads, the reload event, the launch
flow). That needs `docker compose -f docker-compose.demo.yaml up -d` + a peak-assignment run.

### Full task list

Tasks are cut so they can be handed to separate agents with minimal collision. **F1 is the foundation**
— it freezes the store API and delivers `BaseTierTag`, which every other frontend task consumes — so it
lands first. The two backend tasks are independent of F1 and of each other and can start immediately.
Once F1 is in, F2–F5 touch disjoint files and parallelize freely.

| ID | Task | Files (primary) | Depends on | Notes |
|---|---|---|---|---|
| **F1** | Store spine + tier tag | `stores/data/modules/peakAssignment/{run,assignment}.js`, `stores/data/index.js`, `lib/base/BaseTierTag.vue` | GET endpoints (landed) | **The shared contract.** §2. Do first. |
| **B1** | `peak_assignment_reload` event | `api/new/peak_assignments/service.py` (finalize path) + the socket emit helper used by `match_reload` | — | Small. Mirror `match_reload`. §2.3. |
| **B2** | Composition-driven Fit visualization | new endpoint(s) beside `/match/aggregate/.../ion` + `/visualization/ion_focus` | — | Larger. Accept formula + mechanism + sample; return the same `{match_ions, match_isotopes}` shape. §4. |
| **F2** | Peak ledger | `PaneBrowserPeak.vue` | F1 | Reads `byPeakId`, `tierCounts`. §3. |
| **F3** | Peak inspector | `PanePeakAssign.vue` | F1 | Winner + evidence + `alternatives`; existing search → "Re-search". §3. |
| **F4** | Annotated spectrum | `ChartSampleSpectrum/data.js` | F1 | Per-tier Plotly traces from `byPeakId`. §3. |
| **F5** | Assignments browser + run selector + config dialog | `PaneBrowserMatch.vue`, new run-config dialog | F1; **B1** for live refresh | Coexist "Targets"/"Assignments"; row click focuses the peak. §3. |
| **F6** | Fit view rename + composition wiring | `Dashboard.vue` (label), `match/visualized.js` | **B2** | Rename now; composition branch when B2's contract is fixed. §4. |

**Suggested sequencing**

1. **Now, in parallel:** F1 (foundation), B1, B2.
2. **After F1:** F2, F3, F4, F5 in parallel; F5 stubs the refresh until B1 lands.
3. **After B2:** F6.

**Collision map.** The only shared frontend surfaces are `stores/data/index.js` and `BaseTierTag.vue`,
both **owned by F1** and consumed read-only thereafter. F2 (`PaneBrowserPeak`), F4
(`ChartSampleSpectrum`), and F5 (`PaneBrowserMatch`) are disjoint files; F3 (`PanePeakAssign`) is
disjoint from all of them. So post-F1 the frontend work has no file overlap.

**Branching.** Backend tasks (B1, B2) branch off `epic/peak-centric-assignment`. Frontend tasks branch
off `design/peak-centric-frontend` (which already carries this doc), or off F1's branch once it lands,
then merge back to epic. Keep each task a `feat(peak-assignments): …` / `feat(frontend): …` commit.

**Read-path note.** No backend change is needed for reads: the `read` handler's `data.data` unwrap means
run metadata comes from the runs endpoint (via the run store), not the `{run, data}` envelope. If a
future call wants the envelope's `run` inline, add a dedicated handler rather than reusing `read`.
