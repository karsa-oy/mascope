<script setup>
import { ref } from 'vue'

import Button from 'primevue/button'
import Popover from 'primevue/popover'

import BaseParamField from '@/lib/base/BaseParamField.vue'

const chartSettings = ref()
const scale = defineModel('scale')
</script>

<template>
  <Button
    v-tooltip.bottom="'Chart settings'"
    severity="secondary"
    @click="
      (event) => {
        chartSettings.toggle(event)
      }
    "
    icon="pi pi-chart-bar"
  />
  <Popover ref="chartSettings">
    <div class="row" style="padding: 1rem; gap: 0.5rem">
      <BaseParamField
        label="Intensity scale"
        v-model:param="scale"
        :range="{ min: 0, max: 100000, step: 2000 }"
      />
    </div>
  </Popover>
</template>

<style scoped>
:deep(fieldset) {
  flex-flow: column nowrap;
  align-items: stretch;
  gap: 0.5rem;
}
</style>
