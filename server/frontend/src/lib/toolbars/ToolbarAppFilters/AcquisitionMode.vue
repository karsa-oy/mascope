<script setup>
import { reactive } from 'vue'

import SelectButton from 'primevue/selectbutton'

import { DialogSampleOp } from '@/lib/dialogs'
import { useApp } from '@/stores'
import { watchEffect } from 'vue'

const app = useApp()

app.data.acquisition.mode = false

const dialog = reactive({
  sample: null
})

watchEffect(() => {
  if (!app.data.batch.focused) {
    app.data.acquisition.mode = false
  }
})
</script>

<template>
  <div id="measurement-mode" class="hidden">
    {{ app.data.acquisition.mode ? 'active' : '' }}
  </div>
  <SelectButton
    v-model="app.data.acquisition.mode"
    :options="[
      {
        id: 'stop-measuring',
        tooltip: app.data.acquisition.mode ? 'Pause' : 'Paused',
        value: false,
        icon: 'pi pi-pause'
      },
      {
        id: 'start-measuring',
        tooltip: app.data.acquisition.mode ? 'Measuring' : 'Measure',
        value: true,
        icon: 'pi pi-play'
      }
    ]"
    optionLabel="tooltip"
    optionValue="value"
    dataKey="value"
    :class="app.data.acquisition.mode ? 'measure-mode' : ''"
    style="height: 32px"
    :disabled="!app.data.batch.focused"
    :allowEmpty="false"
    :pt="
      app.ui.help.bottom(`
          <h1>Measurement mode controls</h1>

          <p>Enable or disable measurement mode. In measurement
          mode, sample acquisition automatically launches a dialog
          to input data for incoming samples.</p>
    `)
    "
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
  <DialogSampleOp v-model:action="dialog.sample" />
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
