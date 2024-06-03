<script setup>
import { ref, computed } from 'vue'

import ToggleSwitch from 'primevue/toggleswitch'

import { BaseParamField } from '@/lib/base'

import BaseChartPlotly from '../BaseChartPlotly.vue'

import { useData } from './data'

const data = useData()

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
</script>

<template>
  <figure style="position: relative">
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
    />
  </figure>
</template>
