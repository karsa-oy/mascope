<script setup>
import BatchTable from './BatchTable.vue'
import SampleTable from './SampleTable.vue'

import { useApp } from '@/stores'

const app = useApp()
</script>

<template>
  <BatchTable v-if="!app.data.batch.focused" />
  <SampleTable v-else />
</template>
