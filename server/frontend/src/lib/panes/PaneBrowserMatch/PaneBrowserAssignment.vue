<script setup>
import { ref, reactive, computed, inject, onMounted } from 'vue'

import Button from 'primevue/button'
import Select from 'primevue/select'
import Dialog from 'primevue/dialog'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import ProgressSpinner from 'primevue/progressspinner'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import ToggleSwitch from 'primevue/toggleswitch'
import FloatLabel from 'primevue/floatlabel'

import { BaseTabbedPanel, BaseTierTag } from '@/lib/base'
import { num } from '@/lib/formatters'
import { api } from '@/api'
import { useApp } from '@/stores'

const app = useApp()
const tableHeight = inject('match-table-height', ref(300))

const runs = computed(() => app.data.peakAssignment.run)
const assignments = computed(() => app.data.peakAssignment.peak)
const tierCounts = computed(() => assignments.value.tierCounts)

// --- Run selector -----------------------------------------------------------

// One dropdown option per run, labelled with its ordinal, status and age.
const runOptions = computed(() =>
  runs.value.list.map((run, index) => ({
    ...run,
    _label: `#${runs.value.list.length - index} · ${run.status}${
      run.status === 'completed' ? '' : '…'
    }`
  }))
)

const selectedRun = computed({
  get: () => runs.value.focused,
  set: (run) => (run ? runs.value.focus(run) : runs.value.unfocus())
})

// --- Launch a run -----------------------------------------------------------

const configVisible = ref(false)
const submitting = ref(false)
const config = reactive({
  run_untargeted: true,
  mz_precision_ppm: 5,
  formula_ranges: '',
  max_untargeted_peaks: 300,
  peak_intensity_threshold: 0,
  max_alternatives: 5
})

// Prefill m/z precision and formula range from the cheminfo defaults, matching
// the single-peak search in PanePeakAssign.
onMounted(() => {
  api.http
    .get('/params', { type: 'read_params' })
    .then(({ data }) => {
      const cheminfo = data?.data?.params?.cheminfo_config
      if (cheminfo) {
        config.mz_precision_ppm = cheminfo.DEFAULT_MZ_PRECISION ?? config.mz_precision_ppm
        config.formula_ranges = cheminfo.DEFAULT_FORMULA_RANGE ?? config.formula_ranges
      }
    })
    .catch(() => {})
})

async function launch() {
  const sampleItemId = app.data.sample.focusedId
  if (!sampleItemId) return
  submitting.value = true
  try {
    // Omit an empty formula range so the backend default applies.
    const payload = { ...config }
    if (!payload.formula_ranges) delete payload.formula_ranges
    await runs.value.assign(sampleItemId, payload)
    configVisible.value = false
  } finally {
    submitting.value = false
  }
}

// --- Focus a peak from the ledger -------------------------------------------

// Clicking an assignment focuses the matching peak (join by peak_id ===
// sample_peak_id) and brings the Sample tab (spectrum + inspector) forward.
function focusPeak(assignment) {
  const peak = app.data.peak.list.find(
    (p) => String(p.peak_id) === String(assignment.sample_peak_id)
  )
  if (peak) {
    app.data.peak.focus(peak)
    app.ui.tab.active = 'sample'
  }
}

// --- Tier ordering & filtering ----------------------------------------------

// Confidence order: identified first, unassigned last. Drives the default sort
// and makes the sortable tier column order by confidence rather than
// alphabetically (which otherwise put "unassigned" above "identified").
const TIER_RANK = {
  identified: 0,
  candidate: 1,
  below_assignability: 2,
  unassigned: 3
}

// Histogram bucket for a row: reagent/artifact roles are their own bucket,
// matching the counts strip and the spectrum coloring.
function bucketOf(row) {
  if (row.role === 'reagent' || row.role === 'artifact') return 'reagent'
  return row.tier in TIER_RANK ? row.tier : 'unassigned'
}

// Active tier filters (empty = show all); clicking a histogram chip toggles it.
const activeTiers = reactive(new Set())
function toggleTier(key) {
  if (activeTiers.has(key)) activeTiers.delete(key)
  else activeTiers.add(key)
}

// Table rows: one per assigned formula (M0) plus unassigned/reagent peaks;
// iso_child satellites are folded away (they surface in the inspector), which
// also keeps this a flat, fixed-height list compatible with virtual scrolling.
// Filtered by the active chips, then ordered by confidence (identified first)
// and fit descending. tierRank lets the tier column sort by confidence too.
const rows = computed(() => {
  const list = assignments.value.list
    .filter((row) => row.role !== 'iso_child')
    .filter((row) => activeTiers.size === 0 || activeTiers.has(bucketOf(row)))
    .map((row) => ({ ...row, tierRank: TIER_RANK[row.tier] ?? 3 }))
  list.sort((a, b) => a.tierRank - b.tierRank || (b.fit_score ?? -1) - (a.fit_score ?? -1))
  return list
})

// Two-way selection tied to the focused peak: clicking a row focuses its peak,
// and focusing a peak elsewhere (spectrum click, inspector) highlights its row.
// When a folded-out isotopologue is focused, highlight its M0 row.
const selectedRow = computed({
  get: () => {
    const focused = app.data.peak.focused
    if (!focused) return null
    const assignment = assignments.value.forPeak(focused.peak_id)
    const ownerId =
      assignment?.role === 'iso_child'
        ? assignment.owner_peak_assignment_id
        : assignment?.peak_assignment_id
    if (ownerId != null) return rows.value.find((r) => r.peak_assignment_id === ownerId) ?? null
    return rows.value.find((r) => String(r.sample_peak_id) === String(focused.peak_id)) ?? null
  },
  set: (row) => {
    if (row) focusPeak(row)
  }
})

// Isotopologue satellites folded under a formula's M0.
const isoCount = (row) => assignments.value.childrenOf(row.peak_assignment_id).length
</script>

<template>
  <BaseTabbedPanel label="Assignments" icon="pi ph ph-list-magnifying-glass">
    <template #menu>
      <div class="menu-row">
        <Select
          v-if="runOptions.length"
          v-model="selectedRun"
          :options="runOptions"
          optionLabel="_label"
          dataKey="peak_assignment_run_id"
          size="small"
          placeholder="Select run"
          style="min-width: 12rem"
        />
        <Button
          label="Assign peaks"
          icon="pi ph ph-magic-wand"
          size="small"
          :disabled="!app.data.sample.focused"
          @click="configVisible = true"
        />
      </div>
    </template>

    <div v-if="!runs.list.length" class="center empty">
      <div class="col" style="gap: 0.75rem; text-align: center; max-width: 40ch">
        <strong><span class="pi ph ph-info" /> No assignment runs</strong>
        <i style="opacity: 0.6">
          Assign a composition to every peak in this sample: first from the known target library,
          then via untargeted composition search.
        </i>
        <Button
          label="Assign peaks"
          icon="pi ph ph-magic-wand"
          size="small"
          :disabled="!app.data.sample.focused"
          @click="configVisible = true"
        />
      </div>
    </div>

    <div v-else class="col" style="gap: 0.6rem; align-items: stretch">
      <div class="tier-strip">
        <button
          v-for="t in [
            { key: 'identified', label: 'identified', count: tierCounts.identified },
            { key: 'candidate', label: 'candidate', count: tierCounts.candidate },
            { key: 'reagent', label: 'reagent', count: tierCounts.reagent },
            { key: 'below_assignability', label: 'below', count: tierCounts.below_assignability },
            { key: 'unassigned', label: 'unassigned', count: tierCounts.unassigned }
          ]"
          :key="t.key"
          type="button"
          class="tier-stat"
          :class="[
            t.key === 'below_assignability' ? 'below' : t.key,
            {
              active: activeTiers.has(t.key),
              dim: activeTiers.size && !activeTiers.has(t.key)
            }
          ]"
          v-tooltip.top="activeTiers.has(t.key) ? `Showing only ${t.label}` : `Filter to ${t.label}`"
          @click="toggleTier(t.key)"
        >
          <b>{{ t.count }}</b> {{ t.label }}
        </button>
      </div>

      <div v-if="assignments.pending" class="center loading-region">
        <ProgressSpinner />
      </div>
      <DataTable
        v-else
        :value="rows"
        dataKey="sample_peak_id"
        size="small"
        scrollable
        :scrollHeight="`${tableHeight - 60}px`"
        :virtualScrollerOptions="{ itemSize: 35.5 }"
        sortField="tierRank"
        :sortOrder="1"
        selectionMode="single"
        :metaKeySelection="false"
        v-model:selection="selectedRow"
      >
        <Column field="sample_peak_mz" header="m/z" sortable style="min-width: 6rem">
          <template #body="{ data }">{{ num.mz.format(data.sample_peak_mz) }}</template>
        </Column>
        <Column
          field="sample_peak_intensity"
          header="intensity"
          sortable
          style="min-width: 5rem"
        >
          <template #body="{ data }">
            {{
              data.sample_peak_intensity != null
                ? num.peakIntensity.format(data.sample_peak_intensity)
                : '—'
            }}
          </template>
        </Column>
        <Column field="assigned_formula" header="formula" sortable style="min-width: 6rem">
          <template #body="{ data }">
            <span class="formula">{{ data.assigned_formula || '—' }}</span>
            <span
              v-if="isoCount(data)"
              class="iso-count"
              v-tooltip.top="`${isoCount(data)} isotopologue peak${isoCount(data) === 1 ? '' : 's'}`"
              >+{{ isoCount(data) }}</span
            >
          </template>
        </Column>
        <Column field="tierRank" header="tier" sortable style="min-width: 7rem">
          <template #body="{ data }">
            <BaseTierTag
              :tier="data.tier"
              :fit-score="data.fit_score"
              :role="data.role"
              :source="data.source"
            />
          </template>
        </Column>
      </DataTable>
    </div>

    <Dialog
      v-model:visible="configVisible"
      modal
      header="Assign peaks"
      :style="{ width: '26rem' }"
    >
      <div class="col config-form" style="gap: 1.25rem; align-items: stretch">
        <div class="toggle-row">
          <ToggleSwitch v-model="config.run_untargeted" inputId="run_untargeted" />
          <label for="run_untargeted">
            Untargeted search
            <small>Search compositions for peaks the library leaves unassigned.</small>
          </label>
        </div>
        <FloatLabel>
          <InputNumber
            v-model="config.mz_precision_ppm"
            inputId="mz_precision_ppm"
            :min="1"
            :max="100"
            fluid
          />
          <label for="mz_precision_ppm">m/z precision (ppm)</label>
        </FloatLabel>
        <FloatLabel>
          <InputText v-model="config.formula_ranges" id="formula_ranges" fluid />
          <label for="formula_ranges">Formula range</label>
        </FloatLabel>
        <FloatLabel>
          <InputNumber
            v-model="config.max_untargeted_peaks"
            inputId="max_untargeted_peaks"
            :min="1"
            fluid
          />
          <label for="max_untargeted_peaks">Max untargeted peaks</label>
        </FloatLabel>
        <FloatLabel>
          <InputNumber
            v-model="config.peak_intensity_threshold"
            inputId="peak_intensity_threshold"
            :min="0"
            fluid
          />
          <label for="peak_intensity_threshold">Peak intensity threshold</label>
        </FloatLabel>
        <FloatLabel>
          <InputNumber
            v-model="config.max_alternatives"
            inputId="max_alternatives"
            :min="0"
            fluid
          />
          <label for="max_alternatives">Max alternatives kept</label>
        </FloatLabel>
      </div>
      <template #footer>
        <Button label="Cancel" text severity="secondary" @click="configVisible = false" />
        <Button label="Assign" icon="pi ph ph-magic-wand" :loading="submitting" @click="launch" />
      </template>
    </Dialog>
  </BaseTabbedPanel>
</template>

<style scoped>
.empty {
  width: 100%;
  height: 220px;
}
.loading-region {
  width: 100%;
  min-height: 10rem;
}

.tier-strip {
  display: flex;
  flex-flow: row wrap;
  gap: 0.3rem;
  padding: 0 0.4rem;
}
.tier-stat {
  font-size: 0.72rem;
  padding: 0.15rem 0.5rem;
  border-radius: 100px;
  border: 1px solid var(--p-content-border-color, #e3e6ec);
  font-variant-numeric: tabular-nums;
  /* button reset */
  background: transparent;
  color: inherit;
  font-family: inherit;
  cursor: pointer;
  transition: opacity 0.12s, border-color 0.12s, background 0.12s;
}
.tier-stat:hover {
  border-color: var(--p-primary-color, #6366f1);
}
.tier-stat.active {
  border-color: var(--p-primary-color, #6366f1);
  background: color-mix(in srgb, var(--p-primary-color, #6366f1) 12%, transparent);
}
.tier-stat.dim {
  opacity: 0.4;
}
.tier-stat b {
  font-weight: 700;
}
.tier-stat.identified b {
  color: var(--p-green-600, #1f9d63);
}
.tier-stat.candidate b {
  color: var(--p-amber-600, #c9861f);
}
.tier-stat.reagent b {
  color: #8a5ed0;
}
.tier-stat.below b,
.tier-stat.unassigned b {
  color: var(--p-surface-500, #6f7889);
}

.formula {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.82rem;
}
.iso-count {
  margin-left: 0.35rem;
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.62rem;
  opacity: 0.55;
  vertical-align: super;
}

.menu-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.toggle-row {
  display: flex;
  align-items: flex-start;
  gap: 0.6rem;
}
.toggle-row label {
  display: flex;
  flex-direction: column;
  font-size: 0.9rem;
}
.toggle-row small {
  opacity: 0.6;
  font-size: 0.75rem;
}
</style>
