<script setup>
import Panel from 'primevue/panel'
import TabMenu from 'primevue/tabmenu'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'

import { num } from '@/lib/formatters'
import { useApp } from '@/stores'

const app = useApp()

const props = defineProps({
  height: {
    type: Number,
    required: true
  }
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
      <span style="opacity: 0.5">{{ app.data.peak.list.length }} peaks detected </span></template
    >
    <DataTable
      :value="app.data.peak.list"
      dataKey="peak_id"
      selectionMode="single"
      :metaKeySelection="false"
      v-model:selection="app.data.peak.focused"
      sortField="area"
      :sortOrder="-1"
      size="small"
      scrollable
      :scrollHeight="`${height}px`"
      :virtualScrollerOptions="{ itemSize: 20 }"
    >
      <Column field="mz" header="m/z" sortable style="height: 20px">
        <template #body="{ data }">
          {{ num.mz.format(data.mz) }}
        </template>
      </Column>
      <Column field="height" header="height" sortable style="height: 20px">
        <template #body="{ data }">
          {{ num.peakIntensity.format(data.height) }}
        </template>
      </Column>
      <Column field="area" header="area" sortable style="height: 20px">
        <template #body="{ data }">
          {{ num.peakIntensity.format(data.area) }}
        </template>
      </Column>
      <Column field="target_isotope_formula" header="formula" sortable style="height: 20px">
        <template #body="{ data }">
          {{ data.target_isotope_formula }}
        </template>
      </Column>
    </DataTable>
  </Panel>
</template>

<style scoped>
:deep(.p-panel-header) {
  display: flex !important;
}
</style>
