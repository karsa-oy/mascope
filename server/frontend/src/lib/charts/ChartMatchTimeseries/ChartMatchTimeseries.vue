<script setup>
import { ref, computed, toRaw, watch, onMounted } from 'vue'

import Tag from 'primevue/tag'

import { useApp } from '@/stores'
import { num } from '@/lib/formatters'

import BaseChartPlotly from '../BaseChartPlotly.vue'
import { useChartData } from './data.js'
import { ToolbarIntensityScale } from '@/lib/toolbars'

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

watch(
  () => app.data.match.visualized.isotopes,
  () => {
    // Reset zoom when data changes
    if (plot.value !== null) {
      plot.value.resetZoom()
    }
  }
)

onMounted(() => {
  scale.value.log = true
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
    type: scale.value.log ? 'log' : 'lin',
    gridcolor: '#33333399',
    gridwidth: 1,
    autorange: true
  },
  margin: { l: 50, r: 30, t: 30, b: 40 },
  dragmode: 'zoom',
  showlegend: true,
  legend: {
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
    <div style="width: 100%; min-width: 0; overflow: hidden">
      <BaseChartPlotly
        id="ChartMatchTimeseries"
        ref="plot"
        title="Timeseries"
        :data="traces"
        :layout="layout"
      >
        <template v-slot:settings>
          <ToolbarIntensityScale v-model="scale" />
        </template>
      </BaseChartPlotly>
    </div>
  </figure>
</template>
