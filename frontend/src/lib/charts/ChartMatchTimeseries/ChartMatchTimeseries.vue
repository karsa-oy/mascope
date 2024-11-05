<script setup>
import { computed } from 'vue'
import Tag from 'primevue/tag'

import { useApp } from '@/stores'

import BaseChartPlotly from '../BaseChartPlotly.vue'

import { useChartData } from './data.js'

const app = useApp()

const data = useChartData()

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
        :value="corr.format(app.data.match.visualized.isotopes[0].match_isotope_correlation)"
        :severity="
          Math.abs(app.data.match.visualized.isotopes[0].match_isotope_correlation) >
          app.data.match.params.current.min_isotope_correlation
            ? 'info'
            : 'warn'
        "
      />
    </span>
    <BaseChartPlotly
      id="ChartMatchTimeseries"
      title="Timeseries"
      :data="data.traces"
      :layout="layout"
    />
  </figure>
</template>
