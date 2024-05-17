<script setup>
import { reactive, computed, watch } from 'vue'

import SelectButton from 'primevue/selectbutton'

import { DialogSampleItemOp } from '@/lib/dialogs'
import { useAppStore, useInstrumentStore, useBatchStore } from '@/stores'

const appStore = useAppStore()
const batchStore = useBatchStore()
const instrumentStore = useInstrumentStore()

appStore.mode.measuring = false

const dialog = reactive({
  sampleItem: null
})

watch(
  computed(() => dialog.sampleItem == null),
  update
)
function update(closing) {
  if (closing) {
    instrumentStore.resetAcquisitionStatus()
  }
}
</script>

<template>
  <SelectButton
    v-model="appStore.mode.measuring"
    :options="[
      {
        tooltip: appStore.mode.measuring  ? 'Pause' : 'Paused',
        value: false,
        icon: 'pi pi-pause'
      },
      {
        tooltip: appStore.mode.measuring  ? 'Measuring' : 'Measure',
        value: true,
        icon: 'pi pi-play'
      }
    ]"
    optionValue="value"
    optionLabel="label"
    dataKey="value"
    :class="appStore.mode.measuring  ? 'k-measuremode' : ''"
    style="height: 32px"
    :disabled="!batchStore.active"
    :allowEmpty="false"
  >
    <template #option="{ option }">
      <div style="z-index: 100" :class="option.icon" v-tooltip.bottom="option.tooltip" />
    </template>
  </SelectButton>
  <DialogSampleItemOp v-model:action="dialog.sampleItem" />
</template>

<style scoped>
@property --dark {
  syntax: '<color>';
  initial-value: white;
  inherits: false;
}
@property --light {
  syntax: '<color>';
  initial-value: white;
  inherits: false;
}

.k-measuremode :deep(.p-togglebutton.p-togglebutton-checked::before) {
  background-color: var(--light);
  border: 1px solid var(--dark);
  transition:
    --dark 1s,
    --light 1s;
}
</style>
