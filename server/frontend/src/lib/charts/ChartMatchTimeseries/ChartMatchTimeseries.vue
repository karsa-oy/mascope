<script setup>
import { ref, computed, toRaw } from 'vue'

import Tag from 'primevue/tag'

import { useApp } from '@/stores'
import { num } from '@/lib/formatters'

import BaseChartPlotly from '../BaseChartPlotly.vue'
import { useChartData } from './data.js'

const app = useApp()
const data = useChartData()

const scale = defineModel()

const props = defineProps({
  height: {
    type: Number,
    required: false
  }
})

const plot = ref(null)

const sampleLength = computed(() =>
  // Length of the selected sample in seconds
  app.data.sample.selected.length != 1 ? null : app.data.sample.selected[0].length
)

const traces = computed(() => {
  if (plot.value === null) return []
  // Reset zoom when data changes
  plot.value.resetZoom()
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
    title: { text: 'Time [s]' },
    autorange: true,
    showgrid: true,
    gridcolor: '#33333399',
    gridwidth: 1,
    autorange: true
  },
  yaxis: {
    title: { text: `Peak intensity [counts/s]` },
    showgrid: true,
    autorange: true,
    rangemode: 'tozero',
    gridcolor: '#33333399',
    gridwidth: 1,
    autorange: true
  },
  margin: { l: 50, r: 30, t: 30, b: 40 },
  dragmode: 'zoom',
  showlegend: true,
  legend: {
    xanchor: 'right',
    x: 1,
    y: 1
  },
  height: props.height
}))
</script>

<template>
  <figure
    v-if="app.data.match.visualized.isotopes?.length"
    style="padding: 0; margin: 0; width: 100%; min-width: 0; overflow: hidden; flex-shrink: 1"
  >
    <span style="margin-bottom: 1rem">
      isotope similarity:
      <Tag
        :value="
          num.isotopeSimilarity.format(
            app.data.match.visualized.isotopes?.[0].match.match_isotope_similarity
          )
        "
      />
    </span>
    <div style="width: 100%; min-width: 0; overflow: hidden">
      <BaseChartPlotly
        id="ChartMatchTimeseries"
        ref="plot"
        title="Timeseries"
        :data="traces"
        :layout="layout"
      />
    </div>
  </figure>
</template>
