<script setup>
import { computed } from 'vue'

import BatchTable from './BatchTable.vue'
import SampleTable from './SampleTable.vue'

import { useApp } from '@/stores'

const app = useApp()

const batch = computed(() => ({
  ...app.data.batch.focused,
  children:
    app.data.sample.list?.filter((sample) => sample.sample_batch_id == app.data.batch.focusedId) ??
    []
}))
</script>

<template>
  <BatchTable v-if="!app.data.batch.focused" />
  <SampleTable v-else :batch="batch" />
</template>
