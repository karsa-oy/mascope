<script setup>
import Panel from 'primevue/panel'
import Button from 'primevue/button'
import TabMenu from 'primevue/tabmenu'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import ContextMenu from 'primevue/contextmenu'

import { BaseCopyableField } from '@/lib/base'
import { useApp } from '@/stores'

const app = useApp()

const formatter = new Intl.NumberFormat('en-US', {
  minimumIntegerDigits: 2,
  minimumFractionDigits: 3,
  maximumFractionDigits: 3
})
</script>

<template>
  <Panel class="browser" style="border: none; width: 400px" v-if="app.data.peak.list.length > 0">
    <template #header>
      <TabMenu :model="[{ label: 'Peaks', icon: 'pi ph ph-crosshair' }]" style="overflow: hidden" />
    </template>
    <template #icons>
      <span style="opacity: 0.5">{{ app.data.peak.list.length }} peaks detected </span></template
    >
    <DataTable
      :value="app.data.peak.list"
      dataKey="mz"
      selectionMode="single"
      :metaKeySelection="false"
      v-model:selection="app.data.peak.focused"
      sortField="area"
      :sortOrder="-1"
      size="small"
      scrollable
      scrollHeight="340px"
    >
      <Column field="mz" header="m/z" sortable>
        <template #body="{ data }">
          {{ formatter.format(data.mz) }}
        </template>
      </Column>
      <Column field="height" header="height" sortable>
        <template #body="{ data }">
          {{ formatter.format(data.height) }}
        </template>
      </Column>
      <Column field="area" header="area" sortable>
        <template #body="{ data }">
          {{ formatter.format(data.area) }}
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
