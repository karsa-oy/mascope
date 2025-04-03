<script setup>
import BatchTable from './BatchTable.vue'
import SampleTable from './SampleTable.vue'
import SampleTableCustomizer from './SampleTableCustomizer.vue'
import SampleContextMenu from './SampleContextMenu.vue'
</script>

<template>
  <BatchTable>
    <template #toolbar>
      <SampleTableCustomizer />
    </template>
    <template #expansion="{ batch }">
      <SampleTable :batch="batch" />
    </template>
  </BatchTable>
  <SampleContextMenu />
</template>
