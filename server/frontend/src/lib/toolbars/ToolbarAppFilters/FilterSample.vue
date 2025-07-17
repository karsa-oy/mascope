<script setup>
import { computed, inject } from 'vue'

import Chip from 'primevue/chip'

import { useApp } from '@/stores'
import { prettyTrim } from '@/lib/utils'

const app = useApp()

const active = computed(() => app.data.batch.focused || app.data.sample.focused)

const register = inject('register-filter')
register({
  clear: () => app.data.batch.unfocus(),
  active
})

const label = computed(() => {
  const batchName = app.data.batch.focused?.sample_batch_name
  if (!batchName) {
    return null
  }
  const sampleCount = app.data.sample.selected.length
  if (sampleCount === 0) {
    return {
      short: prettyTrim(batchName),
      full: `Batch selected
            ${batchName}`
    }
  } else if (sampleCount === 1) {
    const sampleName = app.data.sample.focused?.sample_item_name
    return {
      short: `${prettyTrim(batchName)} ❯ ${prettyTrim(sampleName)}`,
      full: `Sample selected
             ${batchName} ❯ ${sampleName}`
    }
  } else {
    const samplesLabel = `${sampleCount} Samples`
    return {
      short: `${prettyTrim(batchName)} ❯ ${samplesLabel}`,
      full: `Samples selected
             ${batchName} ❯ ${samplesLabel}`
    }
  }
})
</script>

<template>
  <Chip
    v-if="active"
    icon="pi pi-tags"
    :label="label.short"
    v-tooltip.bottom="label.full"
    removable
    @remove="app.data.batch.unfocus()"
  />
</template>
