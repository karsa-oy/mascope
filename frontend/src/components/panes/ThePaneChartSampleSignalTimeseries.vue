<script setup>
import { computed } from 'vue'

import BaseChartPlotly from '@/components/base/BaseChartPlotly.vue'

import { useVisualizationStore } from '@/stores'

const visualizationStore = useVisualizationStore()

const data = computed(() => visualizationStore.tracesSignalTimeseries ?? [])
const layout = computed(() => ({
  xaxis: {
    title: 'Time [s]',
    autorange: true,
    showgrid: true,
    gridcolor: '#464752',
    gridwidth: 1
  },
  yaxis: {
    title: 'Peak height [cps]',
    showgrid: true,
    autorange: true,
    rangemode: 'tozero',
    gridcolor: '#464752',
    gridwidth: 1
  },
  dragmode: 'zoom',
  showlegend: true,
  height: '400',
  width: '860'
}))
</script>

<template>
  <base-chart-plotly
    id="ChartSampleSignalTimeseries"
    title="Timeseries"
    :data="data"
    :layout="layout"
  ></base-chart-plotly>
</template>
