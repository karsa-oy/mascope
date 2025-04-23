<script setup>
import { computed, toRaw } from 'vue'

import { useWindowSize } from '@vueuse/core'

import Tag from 'primevue/tag'

import { useApp } from '@/stores'

import BaseChartPlotly from '../BaseChartPlotly.vue'
import { useChartData } from './data.js'

const app = useApp()
const data = useChartData()
const { width } = useWindowSize()

const scale = defineModel()

const props = defineProps({
  height: {
    type: Number,
    required: false
  }
})

const sampleLength = computed(() =>
  // Length of the selected sample in seconds
  app.data.sample.selected.length != 1 ? null : app.data.sample.selected[0].length
)

const traces = computed(() => {
  // Scale trace y-values based on "sum / average" toggle
  if (sampleLength.value === null) {
    return []
  }
  return scale.value.mode == 'average'
    ? data.traces.map((trace) => {
        let newTrace = structuredClone(toRaw(trace))
        newTrace.fill = 'none'
        return newTrace
      })
    : data.traces.toReversed()
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
    title: `Peak intensity [counts/s]`,
    showgrid: true,
    autorange: true,
    rangemode: 'tozero',
    gridcolor: '#33333399',
    gridwidth: 1
  },
  margin: { l: 50, r: 20, t: 30, b: 40 },
  dragmode: 'zoom',
  showlegend: true,
  legend: {
    xanchor: 'right',
    x: 1,
    y: 1
  },
  height: props.height,
  width: width.value * (app.ui.split.right / 100)
}))

const corr = new Intl.NumberFormat('en-US', {
  style: 'percent',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
})
</script>

<template>
  <figure style="padding: 0">
    <span style="margin-bottom: 1rem">
      isotope correlation coefficient:
      <Tag
        :value="corr.format(app.data.match.visualized.isotopes?.[0].match_isotope_correlation)"
        :severity="
          Math.abs(app.data.match.visualized.isotopes?.[0].match_isotope_correlation) >
          app.data.match.params.ui?.min_isotope_correlation
            ? 'info'
            : 'warn'
        "
      />
    </span>
    <BaseChartPlotly
      id="ChartMatchTimeseries"
      title="Timeseries"
      :data="traces"
      :layout="layout"
      :height="height"
    />
  </figure>
</template>
