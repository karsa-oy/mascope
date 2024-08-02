<script setup>
import { ref, computed } from 'vue'

import ToggleSwitch from 'primevue/toggleswitch'
import ProgressSpinner from 'primevue/progressspinner'

import { BaseParamField } from '@/lib/base'

import BaseChartPlotly from '../BaseChartPlotly.vue'

import { useChartData } from './data.js'

const data = useChartData()

const scale = ref()
const log = ref()

const layout = computed(() => ({
  xaxis: {
    title: 'm/z [Th]',
    autorange: true,
    showgrid: true,
    gridcolor: '#33333399',
    gridwidth: 1
  },
  yaxis: {
    title: 'Intensity [cps]',
    showgrid: true,
    rangemode: 'nonnegative',
    gridcolor: '#33333399',
    gridwidth: 1,
    type: log.value ? 'log' : 'lin',
    ...(scale.value
      ? { range: [0, scale.value] }
      : {
          autorange: true
        })
  },
  dragmode: 'zoom',
  showlegend: false
}))

const config = {
  modeBarButtonsToRemove: ['autoScale', 'resetScale2d', 'pan2d']
}
</script>

<template>
  <figure style="position: relative" :class="data.loading ? 'faded' : ''">
    <div
      style="
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        min-height: 100%;
        z-index: 100;
        display: grid;
        place-items: center;
      "
      v-if="data.loading"
    >
      <ProgressSpinner />
    </div>
    <div
      class="row"
      style="width: 100%; max-width: 350px; position: absolute; top: 1rem; left: 0rem; z-index: 100"
    >
      <BaseParamField
        label="Intensity scale"
        v-model:param="scale"
        :range="{ min: 0, max: 100000, step: 2000 }"
        hideSlider
      />
      <ToggleSwitch v-model="log" />
      <span> log scale </span>
    </div>
    <BaseChartPlotly
      id="ChartSampleSpectrum"
      title="Spectrum"
      :data="data.traces"
      :layout="layout"
      :config="config"
    />
  </figure>
</template>

<style scoped>
.faded {
  opacity: 0.3;
}
</style>
