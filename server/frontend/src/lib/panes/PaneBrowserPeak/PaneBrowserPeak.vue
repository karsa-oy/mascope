<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Panel from 'primevue/panel'
import ProgressSpinner from 'primevue/progressspinner'
import TabMenu from 'primevue/tabmenu'

import { num } from '@/lib/formatters'
import { BaseTierTag } from '@/lib/base'
import { useApp } from '@/stores'
import { usePeakScroller } from './stores'

const app = useApp()
const peakTable = ref(null)
const scroller = usePeakScroller()

defineProps({
  height: {
    type: Number,
    required: true
  }
})

// The per-peak assignments of the focused run, joined to peaks by
// String(peak_id) === sample_peak_id (see docs/dev/peak_assignment_frontend.md).
const assignments = computed(() => app.data.peakAssignment.peak)
const hasRun = computed(() => !!assignments.value.run)
const tierCounts = computed(() => assignments.value.tierCounts)

const assignmentFor = (peak) => assignments.value.forPeak(peak?.peak_id)

// Source badge shown next to the committed formula.
const sourceIcon = (source) => {
  switch (source) {
    case 'database':
      return 'pi ph ph-database'
    case 'untargeted':
      return 'pi ph ph-magnifying-glass'
    default:
      return null
  }
}

// Watch for table ref to become available and bind to scroller
watch(
  peakTable,
  (newTableRef) => {
    if (newTableRef) {
      scroller.bind(newTableRef, () => app.data.peak.list)
    }
  },
  { immediate: true }
)

// Watch for focused peak and scroll to it
watch(
  () => app.data.peak.focusedId,
  (peakId) => {
    if (peakId) {
      scroller.scrollToPeak(peakId)
    }
  }
)
// Watch for changes in the peak list and scroll to focused peak if needed
// (after refreshing data)
watch(
  () => app.data.peak.list,
  () => {
    if (app.data.peak.focusedId) {
      scroller.scrollToPeak(app.data.peak.focusedId)
    }
  }
)

onBeforeUnmount(() => {
  scroller.bind(null, () => [])
})
</script>

<template>
  <Panel
    class="browser"
    style="border: none; min-width: 280px; max-width: 400px; width: 100%"
    :pt="
      app.ui.help.top(`
        <h1>Peak Ledger</h1>

        <p>
        Every detected peak in the selected sample and its committed assignment - formula,
        confidence tier and fit score - from the latest assignment run. Click a peak to inspect it.
        </p>
      `)
    "
  >
    <template #header>
      <TabMenu :model="[{ label: 'Peaks', icon: 'pi ph ph-crosshair' }]" style="overflow: hidden" />
    </template>
    <template #icons>
      <span v-if="hasRun" class="tier-summary">
        <span class="tier-stat identified" v-tooltip.bottom="'Identified'">
          {{ tierCounts.identified }}
        </span>
        <span class="tier-stat candidate" v-tooltip.bottom="'Candidate'">
          {{ tierCounts.candidate }}
        </span>
        <span class="tier-stat below" v-tooltip.bottom="'Below assignability'">
          {{ tierCounts.below_assignability }}
        </span>
        <span class="tier-stat unassigned" v-tooltip.bottom="'Unassigned'">
          {{ tierCounts.unassigned }}
        </span>
      </span>
      <span v-else style="opacity: 0.5">{{ app.data.peak.list.length }} peaks &middot; no run</span>
    </template>
    <DataTable
      v-if="!app.data.peak.pending"
      ref="peakTable"
      :value="app.data.peak.list"
      dataKey="peak_id"
      selectionMode="single"
      :metaKeySelection="false"
      v-model:selection="app.data.peak.focused"
      :sortField="scroller.sortField"
      :sortOrder="scroller.sortOrder"
      @sort="(e) => scroller.setSort(e.sortField, e.sortOrder)"
      size="small"
      scrollable
      :scrollHeight="`${height}px`"
      :virtualScrollerOptions="{ itemSize: 35.5 }"
      :pt="{ bodyRow: ({ context }) => ({ id: app.data.peak.list[context.index]?.peak_id }) }"
    >
      <Column field="mz" header="m/z" sortable style="height: 20px; min-width: 6rem">
        <template #body="{ data }">
          {{ num.mz.format(data.mz) }}
        </template>
      </Column>
      <Column field="height" header="height" sortable style="height: 20px; min-width: 5rem">
        <template #body="{ data }">
          {{ num.peakIntensity.format(data.height) }}
        </template>
      </Column>
      <Column header="assignment" style="height: 20px; min-width: 9rem">
        <template #body="{ data }">
          <div v-if="assignmentFor(data)" class="assignment-cell">
            <span class="formula" v-if="assignmentFor(data).assigned_formula">
              <span
                v-if="sourceIcon(assignmentFor(data).source)"
                :class="sourceIcon(assignmentFor(data).source)"
                class="source-icon"
                v-tooltip.top="assignmentFor(data).source"
              />
              {{ assignmentFor(data).assigned_formula }}
            </span>
            <BaseTierTag
              :tier="assignmentFor(data).tier"
              :fit-score="assignmentFor(data).fit_score"
              :role="assignmentFor(data).role"
              :source="assignmentFor(data).source"
            />
          </div>
          <span v-else-if="hasRun" class="empty">&mdash;</span>
        </template>
      </Column>
    </DataTable>
    <div v-else class="center" style="width: 100%; height: 220px">
      <div class="col">
        <ProgressSpinner />
      </div>
    </div>
  </Panel>
</template>

<style scoped>
:deep(.p-panel-header) {
  display: flex !important;
}

:deep(.p-datatable .p-datatable-tbody > tr) {
  height: 36px !important;
}

.assignment-cell {
  display: flex;
  flex-flow: row wrap;
  gap: 0.3rem;
  align-items: center;
}

.formula {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.82rem;
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}

.source-icon {
  opacity: 0.5;
  font-size: 0.8rem;
}

.empty {
  opacity: 0.4;
}

.tier-summary {
  display: inline-flex;
  gap: 0.25rem;
  font-size: 0.72rem;
}

.tier-stat {
  min-width: 1.6rem;
  text-align: center;
  padding: 0.05rem 0.35rem;
  border-radius: 4px;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}
.tier-stat.identified {
  color: var(--p-green-600, #1f9d63);
  background: color-mix(in srgb, var(--p-green-500, #22c55e) 15%, transparent);
}
.tier-stat.candidate {
  color: var(--p-amber-600, #c9861f);
  background: color-mix(in srgb, var(--p-amber-500, #f59e0b) 15%, transparent);
}
.tier-stat.below {
  color: var(--p-surface-500, #6f7889);
  background: color-mix(in srgb, var(--p-surface-500, #6f7889) 12%, transparent);
}
.tier-stat.unassigned {
  color: var(--p-surface-400, #9aa2b1);
  border: 1px dashed color-mix(in srgb, var(--p-surface-400, #9aa2b1) 50%, transparent);
}
</style>
