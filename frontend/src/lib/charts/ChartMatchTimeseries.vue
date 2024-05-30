<script setup>
import { computed } from 'vue'
import Tag from 'primevue/tag'

import BaseChartPlotly from './BaseChartPlotly.vue'

import { useVisualizationStore } from '@/stores'

const visualizationStore = useVisualizationStore()

const data = computed(() => visualizationStore.tracesSignalTimeseries ?? [])
const layout = computed(() => ({
  xaxis: {
    title: 'Time [s]',
    autorange: true,
    showgrid: true,
    gridcolor: '#33333399',
    gridwidth: 1
  },
  yaxis: {
    title: 'Peak height [cps]',
    showgrid: true,
    autorange: true,
    rangemode: 'tozero',
    gridcolor: '#33333399',
    gridwidth: 1
  },
  dragmode: 'zoom',
  showlegend: true
}))

const corr = new Intl.NumberFormat('en-US', {
  style: 'percent',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
})
</script>

<template>
  <figure>
    <span>
      isotope correlation coefficient:
      <Tag
        :value="corr.format(visualizationStore.activeIsotopes[0].match_isotope_correlation)"
        :severity="
          Math.abs(visualizationStore.activeIsotopes[0].match_isotope_correlation) >
          visualizationStore.paramMinIsotopeCorrelation
            ? 'info'
            : 'warn'
        "
      />
    </span>
    <BaseChartPlotly
      id="ChartSampleSignalTimeseries"
      title="Timeseries"
      :data="data"
      :layout="layout"
    />
  </figure>
</template>
