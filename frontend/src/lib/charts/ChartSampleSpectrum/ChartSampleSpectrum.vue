<script setup>
import { ref, computed } from 'vue'

import { BaseParamField } from '@/lib/base'

import BaseChartPlotly from '../BaseChartPlotly.vue'

import { useData } from './data'

const data = useData()

const scale = ref()

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
      style="width: 100%; max-width: 300px; position: absolute; top: 1rem; left: 0rem; z-index: 100"
    >
      <BaseParamField
        label="Intensity scale"
        v-model:param="scale"
        :range="{ min: 0, max: 100000, step: 2000 }"
        hideSlider
      />
    </div>
    <BaseChartPlotly
      id="ChartSampleSpectrum"
      title="Spectrum"
      :data="data.traces"
      :layout="layout"
    />
  </figure>
</template>
