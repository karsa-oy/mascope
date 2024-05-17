<script setup>
import ScrollPanel from 'primevue/scrollpanel'

import { useAppStore } from '@/stores'

const appStore = useAppStore()

const selected = defineModel('selected')
</script>

<template>
  <Panel>
    <ScrollPanel style="width: 100%; height: 300px">
      <DataTable
        v-model:selection="selected"
        :value="appStore.ionMechanisms"
        tableStyle="min-width: 70ch;"
      >
        <Column selectionMode="multiple" />
        <Column header="Mechanism" field="ionization_mechanism" />
        <Column header="Polarity" field="ionization_mechanism_polarity" />
      </DataTable>
    </ScrollPanel>
  </Panel>
</template>
