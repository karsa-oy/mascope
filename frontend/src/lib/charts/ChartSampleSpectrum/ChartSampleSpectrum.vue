<script setup>
import { computed } from 'vue'

import BaseChartPlotly from '../BaseChartPlotly.vue'

import { useData } from './data'

const data = useData()

const layout = computed(() => ({
  xaxis: {
    title: 'Mass [mz]',
    autorange: true,
    showgrid: true,
    gridcolor: '#33333399',
    gridwidth: 1
  },
  yaxis: {
    title: 'Intensity [cps]',
    showgrid: true,
    autorange: true,
    rangemode: 'tozero',
    gridcolor: '#33333399',
    gridwidth: 1
  },
  dragmode: 'zoom',
  showlegend: false
}))
</script>

<template>
  <figure>
    <BaseChartPlotly
      id="ChartSampleSpectrum"
      title="Spectrum"
      :data="data.traces"
      :layout="layout"
    />
  </figure>
</template>
