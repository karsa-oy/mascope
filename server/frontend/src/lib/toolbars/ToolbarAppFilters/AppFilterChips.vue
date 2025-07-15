<script setup>
import { watchEffect, computed } from 'vue'

import { useMagicKeys } from '@vueuse/core'

const { alt, c } = useMagicKeys()

watchEffect(() => {
  if (alt.value && c.value) {
    app.data.batch.unfocus()
  }
})

import Chip from 'primevue/chip'

import { useApp } from '@/stores'

const app = useApp()

const filtering = defineModel('filtering')
watchEffect(() => {
  filtering.value = app.data.batch.focused || app.data.sample.focused
})

const trim = (label, length = 15) =>
  label && label.length > length ? label.slice(0, length) + '...' : label

const sampleLabel = computed(() => {
  const batchName = app.data.batch.focused?.sample_batch_name
  if (!batchName) {
    return null
  }
  const sampleCount = app.data.sample.selected.length
  if (sampleCount === 0) {
    return {
      short: trim(batchName),
      full: `Batch selected
            ${batchName}`
    }
  } else if (sampleCount === 1) {
    const sampleName = app.data.sample.focused?.sample_item_name
    return {
      short: `${trim(batchName)} ❯ ${trim(sampleName)}`,
      full: `Sample selected
             ${batchName} ❯ ${sampleName}`
    }
  } else {
    const samplesLabel = `${sampleCount} Samples`
    return {
      short: `${trim(batchName)} ❯ ${samplesLabel}`,
      full: `Samples selected
             ${batchName} ❯ ${samplesLabel}`
    }
  }
})
</script>

<template>
  <menu>
    <span v-if="filtering" class="pi pi-filter" style="opacity: 0.5" />
    <Chip
      v-if="app.data.batch.focused"
      icon="pi pi-tags"
      :label="sampleLabel.short"
      v-tooltip="sampleLabel.full"
      removable
      @remove="app.data.batch.unfocus()"
    />
  </menu>
</template>

<style scoped>
menu {
  display: flex;
  flex-flow: row;
  align-items: center;
  gap: 0.5rem;
  padding: 0;
}
</style>
