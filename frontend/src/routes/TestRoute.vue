<script setup>
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'

import { useSample } from '@/stores/data/sample'

const sample = useSample()
</script>

<template>
  <main>
    <section>
      <h4>sample item</h4>
      <DataTable
        dataKey="sample_item_id"
        :value="sample.list"
        v-model:selection="sample.selected"
        :metaKeySelection="false"
        selectionMode="multiple"
        scrollable
        scrollHeight="300px"
      >
        <Column field="sample_item_id" />
        <Column field="sample_item_name" />
      </DataTable>
    </section>
  </main>
</template>

<style scoped>
main {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
}
section {
  padding: 1rem;
}
</style>
