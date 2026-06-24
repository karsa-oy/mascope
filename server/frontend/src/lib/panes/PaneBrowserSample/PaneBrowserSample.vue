<script setup>
import DatasetTable from './DatasetTable.vue'
import BatchTable from './BatchTable.vue'
import SampleTable from './SampleTable.vue'

import { useApp } from '@/stores'

const app = useApp()
</script>

<template>
  <DatasetTable v-if="!app.data.dataset.focused" />
  <BatchTable v-else-if="!app.data.batch.focused" />
  <SampleTable v-else />
</template>
