<script setup>
import { reactive } from 'vue'

import SelectButton from 'primevue/selectbutton'

import { DialogSampleItemOp } from '@/lib/dialogs'
import { useAppStore, useBatchStore } from '@/stores'
import { watchEffect } from 'vue'

const appStore = useAppStore()
const batchStore = useBatchStore()

appStore.mode.measuring = false

const dialog = reactive({
  sampleItem: null
})

watchEffect(() => {
  if (!batchStore.active) {
    appStore.mode.measuring = false
  }
})
</script>

<template>
  <div id="measurement-mode" class="hidden">
    {{ appStore.mode.measuring ? 'active' : '' }}
  </div>
  <SelectButton
    v-model="appStore.mode.measuring"
    :options="[
      {
        id: 'stop-measuring',
        tooltip: appStore.mode.measuring ? 'Pause' : 'Paused',
        value: false,
        icon: 'pi pi-pause'
      },
      {
        id: 'start-measuring',
        tooltip: appStore.mode.measuring ? 'Measuring' : 'Measure',
        value: true,
        icon: 'pi pi-play'
      }
    ]"
    optionValue="value"
    dataKey="value"
    :class="appStore.mode.measuring ? 'k-measuremode' : ''"
    style="height: 32px"
    :disabled="!batchStore.active"
    :allowEmpty="false"
  >
    <template #option="{ option }">
      <div
        :id="option.id"
        style="z-index: 100"
        :class="option.icon"
        v-tooltip.bottom="option.tooltip"
      />
      <label :for="option.id" class="hidden">{{ option.id.replace('-', ' ') }}</label>
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
