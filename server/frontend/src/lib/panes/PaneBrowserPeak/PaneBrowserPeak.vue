<script setup>
import { ref, watch, onBeforeUnmount } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Panel from 'primevue/panel'
import TabMenu from 'primevue/tabmenu'

import { num } from '@/lib/formatters'
import { useApp } from '@/stores'
import { usePeakScroller } from './stores'

const app = useApp()
const peakTable = ref(null)
const scroller = usePeakScroller()

const props = defineProps({
  height: {
    type: Number,
    required: true
  }
})

// Watch for table ref to become available and bind to scroller
watch(
  peakTable,
  (newTableRef) => {
    if (newTableRef) {
      scroller.bind(
        newTableRef,
        () => app.data.peak.list,
        () => ({ sortField: 'height', sortOrder: -1 })
      )
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

onBeforeUnmount(() => {
  scroller.bind(
    null,
    () => [],
    () => ({ sortField: 'height', sortOrder: -1 })
  )
})
</script>

<template>
  <Panel
    class="browser"
    style="border: none; min-width: 280px; max-width: 400px; width: 100%"
    v-if="app.data.peak.list.length > 0"
    :pt="
      app.ui.help.top(`
        <h1>Peak Browser</h1>

        <p>
        List of detected peaks in the currently selected sample. Click on a peak to assign a composition.
        </p>
      `)
    "
  >
    <template #header>
      <TabMenu :model="[{ label: 'Peaks', icon: 'pi ph ph-crosshair' }]" style="overflow: hidden" />
    </template>
    <template #icons>
      <span style="opacity: 0.5"
        >{{
          app.data.peak.list.filter(
            (p) => p.target_isotope_formula !== null && p.target_isotope_formula !== ''
          ).length
        }}/{{ app.data.peak.list.length }}
        peaks matched
      </span></template
    >
    <DataTable
      ref="peakTable"
      :value="app.data.peak.list"
      dataKey="peak_id"
      selectionMode="single"
      :metaKeySelection="false"
      v-model:selection="app.data.peak.focused"
      sortField="height"
      :sortOrder="-1"
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
      <Column field="height" header="height" sortable style="height: 20px; min-width: 6rem">
        <template #body="{ data }">
          {{ num.peakIntensity.format(data.height) }}
        </template>
      </Column>
      <Column field="area" header="area" sortable style="height: 20px; min-width: 6rem">
        <template #body="{ data }">
          {{ num.peakIntensity.format(data.area) }}
        </template>
      </Column>
      <Column field="target_isotope_formula" header="formula" sortable style="height: 20px">
        <template #body="{ data }">
          <div class="formula-buttons">
            <Button
              size="small"
              text
              severity="secondary"
              v-tooltip.top="'Visualize ion match'"
              @click="
                async () => {
                  if (data.match.length > 0) {
                    await app.data.match.visualized.set({
                      sampleId: app.data.sample.focusedId,
                      ionId: data.match[index].target_ion_id,
                      collectionId:
                        data.match[index].target_collection_ids.find(
                          (id) => id === app.data.match.collection.focusedId // In case the currently focused collection is among the matches, prioritize it
                        ) || data.match[index].target_collection_ids[0] // Otherwise just take the first one
                    })
                  }
                }
              "
              v-for="(formula, index) in data.target_isotope_formula?.split('; ')"
            >
              {{ formula }}
            </Button>
          </div>
        </template>
      </Column>
    </DataTable>
  </Panel>
</template>

<style scoped>
:deep(.p-panel-header) {
  display: flex !important;
}

:deep(.p-datatable .p-datatable-tbody > tr) {
  height: 36px !important;
}

.formula-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem;
  align-items: flex-start;
  align-content: center;
}
</style>
