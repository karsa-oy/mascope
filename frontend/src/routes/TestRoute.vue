<script setup>
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'

import { useData } from '@/stores/data'

const data = useData()
</script>

<template>
  <main>
    <section>
      <h4>workspace</h4>
      <DataTable
        dataKey="workspace_id"
        :value="data.workspace.list"
        v-model:selection="data.workspace.focused"
        :metaKeySelection="false"
        selectionMode="single"
      >
        <Column field="workspace_id" />
        <Column field="workspace_name" />
      </DataTable>
    </section>
    <section>
      <h4>sample batch</h4>
      <DataTable
        dataKey="sample_batch_id"
        :value="data.batch.list"
        v-model:selection="data.batch.focused"
        :metaKeySelection="false"
        selectionMode="single"
        scrollable
        scrollHeight="300px"
      >
        <Column field="sample_batch_id" />
        <Column field="sample_batch_name" />
      </DataTable>
    </section>
    <section>
      <h4>sample item</h4>
      <DataTable
        dataKey="sample_item_id"
        :value="data.sample.list"
        v-model:selection="data.sample.selected"
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
