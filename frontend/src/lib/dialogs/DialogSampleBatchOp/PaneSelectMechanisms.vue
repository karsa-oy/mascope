<script setup>
import Panel from 'primevue/panel'
import ScrollPanel from 'primevue/scrollpanel'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'

import { useApp } from '@/stores'

const app = useApp()

const selected = defineModel('selected')
</script>

<template>
  <Panel>
    <ScrollPanel style="width: 100%; height: 300px">
      <DataTable
        v-model:selection="selected"
        :value="app.data.mechanism.list"
        tableStyle="min-width: 70ch;"
      >
        <Column selectionMode="multiple" />
        <Column header="Mechanism" field="ionization_mechanism" />
        <Column header="Polarity" field="ionization_mechanism_polarity" />
      </DataTable>
    </ScrollPanel>
  </Panel>
</template>
