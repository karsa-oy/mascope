<script setup>
import { ref, watch } from 'vue'

import Button from 'primevue/button'
import SelectButton from 'primevue/selectbutton'
import ToggleSwitch from 'primevue/toggleswitch'
import FloatLabel from 'primevue/floatlabel'
import Slider from 'primevue/slider'
import InputNumber from 'primevue/inputnumber'

const scale = defineModel()

watch(
  () => [scale.value.mode, scale.value.log],
  () => {
    scale.value.max = null
  }
)
</script>

<template>
  <div class="row">
    <SelectButton v-model="scale.mode" :options="['average', 'sum']" :allowEmpty="false" />
    <ToggleSwitch v-model="scale.log" />
    <span> log scale </span>
  </div>
  <div class="row">
    <FloatLabel>
      <InputNumber
        v-model="scale.max"
        id="intensity-scale-max"
        showButtons
        :min="0"
        :max="1_000_000_000"
        :step="2000"
        :maxFractionDigits="3"
        :allowEmpty="true"
        size="small"
        :disabled="scale.log"
      />
      <label for="intensity-scale-max">Y-range max.</label>
    </FloatLabel>
    <Button
      v-tooltip.right="'Clear scale'"
      severity="secondary"
      text
      @click="
        (event) => {
          scale.max = null
        }
      "
      icon="pi pi-eraser"
      :disabled="scale.max == null"
    />
  </div>
  <Slider
    v-model="scale.max"
    :min="0"
    :max="scale.mode === 'average' ? 100_000 : 1_000_000"
    :step="2000"
    :disabled="scale.log"
    style="margin: 0 0.5rem 1rem 0.5rem"
  />
</template>
