<script setup>
import { computed, toRaw } from 'vue'
import Tag from 'primevue/tag'

import { useApp } from '@/stores'

import BaseChartPlotly from '../BaseChartPlotly.vue'
import { useChartData } from './data.js'

const app = useApp()

const data = useChartData()

const { settings } = defineProps({
  settings: {
    type: Object,
    required: true
  }
})

const sampleLength = computed(() =>
  // Length of the selected sample in seconds
  app.data.sample.selected.length != 1 ? null : app.data.sample.selected[0].length
)

const timeIntervals = computed(() => {
  // Interval between consecutive scans in the sample ("time resolution") in seconds
  if (!data.traces.length) {
    return []
  }
  const t = data.traces[0].x
  // Calculate intervals starting from the second time coordinate
  const tDiff = t.slice(1).map((n, i) => {
    return n - t[i]
  })
  return t[0] > 0
    ? // If first time coordinate is not 0, we use that as the first interval
      [t[0], ...tDiff]
    : // Otherwise use mean interval as the first interval
      [tDiff.reduce((p, c) => p + c, 0) / tDiff.length, ...tDiff]
})

const traces = computed(() => {
  // Scale trace y-values based on "sum / average" toggle
  if (sampleLength.value === null) {
    return []
  }
  return settings.yMode == 'sum'
    ? data.traces.toReversed()
    : data.traces.map((trace) => {
        // Scale chart traces by dividing all y-values by time interval
        let newTrace = structuredClone(toRaw(trace))
        newTrace.y = trace.y.map((value, i) => value / timeIntervals.value[i])
        newTrace.fill = 'none'
        return newTrace
      })
})

const layout = computed(() => ({
  xaxis: {
    title: 'Time [s]',
    autorange: true,
    showgrid: true,
    gridcolor: '#33333399',
    gridwidth: 1
  },
  yaxis: {
    title: `Peak intensity [${data?.unit}${settings.yMode == 'sum' ? '' : '/s'}]`,
    showgrid: true,
    autorange: true,
    rangemode: 'tozero',
    gridcolor: '#33333399',
    gridwidth: 1
  },
  margin: { l: 50, r: 10, t: 30, b: 100 },
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
          app.data.match.params.ui.min_isotope_correlation
            ? 'info'
            : 'warn'
        "
      />
    </span>
    <BaseChartPlotly id="ChartMatchTimeseries" title="Timeseries" :data="traces" :layout="layout" />
  </figure>
</template>
