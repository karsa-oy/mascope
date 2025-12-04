<script setup>
import { computed, inject } from 'vue'

import Chip from 'primevue/chip'

import { useApp } from '@/stores'
import { prettyTrim } from '@/lib/utils'

const app = useApp()

const active = computed(() => app.data.sample.selected.length > 0)

const register = inject('register-filter')
register({
  clear: () => app.data.sample.unfocus(),
  active
})

const label = computed(() => {
  const sampleCount = app.data.sample.selected.length
  if (sampleCount === 1) {
    const sampleName = app.data.sample.focused?.sample_item_name
    return {
      short: `${prettyTrim(sampleName, 30)}`,
      full: `Sample selected:
             ${sampleName}`
    }
  } else {
    const samplesLabel = `${sampleCount} Samples`
    return {
      short: `${samplesLabel}`,
      full: `Samples selected:
             ${samplesLabel}`
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
    @remove="app.data.sample.unfocus()"
  />
</template>
