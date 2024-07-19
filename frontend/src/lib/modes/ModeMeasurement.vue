<script setup>
import { reactive } from 'vue'

import SelectButton from 'primevue/selectbutton'

import { DialogSampleItemOp } from '@/lib/dialogs'
import { useApp } from '@/stores'
import { watchEffect } from 'vue'

const app = useApp()

app.acquisition.mode = false

const dialog = reactive({
  sampleItem: null
})

watchEffect(() => {
  if (!app.data.batch.focused) {
    app.acquisition.mode = false
  }
})
</script>

<template>
  <div id="measurement-mode" class="hidden">
    {{ app.acquisition.mode ? 'active' : '' }}
  </div>
  <SelectButton
    v-model="app.acquisition.mode"
    :options="[
      {
        id: 'stop-measuring',
        tooltip: app.acquisition.mode ? 'Pause' : 'Paused',
        value: false,
        icon: 'pi pi-pause'
      },
      {
        id: 'start-measuring',
        tooltip: app.acquisition.mode ? 'Measuring' : 'Measure',
        value: true,
        icon: 'pi pi-play'
      }
    ]"
    optionLabel="tooltip"
    optionValue="value"
    dataKey="value"
    :class="app.acquisition.mode ? 'measure-mode' : ''"
    style="height: 32px"
    :disabled="!app.data.batch.focused"
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

.measure-mode :deep(.p-togglebutton.p-togglebutton-checked::before) {
  background-color: var(--light);
  border: 1px solid var(--dark);
  transition:
    --dark 1s,
    --light 1s;
}
</style>
