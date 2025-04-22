<script setup>
import { ref, reactive, computed, toRaw, watch, watchEffect } from 'vue'

import SelectButton from 'primevue/selectbutton'
import ToggleSwitch from 'primevue/toggleswitch'
import ProgressSpinner from 'primevue/progressspinner'

import { BaseParamField } from '@/lib/base'
import { useApp } from '@/stores'
import { usePreview } from '@/lib/panes'
import { ToolbarIntensityScale } from '@/lib/toolbars'

import BaseChartPlotly from '../BaseChartPlotly.vue'
import { useChartData } from './data.js'

const app = useApp()
const data = useChartData()

const preview = usePreview()

const props = defineProps({
  height: {
    type: Number,
    required: true
  }
})

const scale = ref({
  mode: 'average',
  max: null,
  log: false
})
const peakAssign = reactive({
  dialog: false,
  mz: null
})

const unit = computed(() =>
  // Adjust the y-axis unit based on "average / sum" toggle
  scale.value.mode == 'average' ? 'counts/s' : 'counts'
)
const sampleLength = computed(() => app.data.sample.focused.length) // duration in seconds

const traces = computed(() =>
  scale.value.mode === 'average'
    ? data.traces
    : data.traces.map((trace) => {
        // Scale chart traces by dividing all y-values by sampleLength
        let newTrace = structuredClone(toRaw(trace))
        newTrace.y = trace.y.map((value) => (value ? value * sampleLength.value : value))
        // For peak traces, scale "customdata" containing [height, area]
        if (newTrace.name.endsWith('Peak')) {
          newTrace.customdata = trace.customdata.map((subarr) => {
            return subarr?.map((value, i) => (i < 2 ? value * sampleLength.value : value))
          })
        }
        return newTrace
      })
)

const zoom = reactive({
  rangeX: null,
  rangeY: null
})

watch(
  () => [scale.value.mode, scale.value.log],
  () => {
    zoom.rangeY = { autorange: true }
  }
)

watchEffect(() => {
  if (app.data.peak.focused) {
    const mz = preview.peak?.mz ?? app.data.peak.focused.mz
    const factor = scale.value.mode == 'sum' ? sampleLength.value : 1
    const height = preview.peak
      ? factor * data.mzRangeMax(mz, 0.3)
      : factor * Math.max(app.data.peak.focused.height, data.mzRangeMax(mz, 0.3))
    zoom.rangeX = { range: [mz - 0.3, mz + 0.3] }
    zoom.rangeY = scale.value.log ? { autorange: true } : { range: [0, height * 1.2] }
  } else {
    zoom.rangeX = null
    zoom.rangeY = null
  }
})

const layout = computed(() => {
  const scaleRangeY =
    scale.value.max && scale.value.max > 0 ? { range: [0, scale.value.max] } : null
  const autorange = { autorange: true }
  const yRange = scaleRangeY ?? zoom.rangeY ?? autorange
  const xRange = zoom.rangeX ?? autorange
  return {
    xaxis: {
      title: 'm/z [Th]',
      showgrid: true,
      gridcolor: '#33333399',
      gridwidth: 1,
      ...xRange
    },
    yaxis: {
      title: `Signal intensity [${unit.value}]`,
      showgrid: true,
      rangemode: 'nonnegative',
      gridcolor: '#33333399',
      gridwidth: 1,
      type: scale.value.log ? 'log' : 'lin',
      ...yRange
    },
    margin: { l: 30, r: 10, t: 45, b: 30 },
    dragmode: 'zoom',
    showlegend: false
  }
})

const config = {
  modeBarButtonsToRemove: ['autoScale', 'resetScale2d', 'pan2d']
}
</script>

<template>
  <BaseChartPlotly
    id="ChartSampleSpectrum"
    title="Spectrum"
    :data="traces"
    :layout="layout"
    :config="config"
    :loading="data.loading"
    @click="
      ({ x, event, data }) => {
        if (event.button === 0 && data.name === 'Peak') {
          app.data.peak.focus({ mz: x })
        }
      }
    "
    @zoom="
      ({ rangeX, rangeY }) => {
        if (rangeX == null && rangeY == null) {
          app.data.peak.unfocus()
        }
        zoom.rangeX = rangeX ?? zoom.rangeX
        zoom.rangeY = rangeY ?? zoom.rangeY
      }
    "
    :height="height"
  >
    <template v-slot:settings>
      <ToolbarIntensityScale v-model="scale" />
    </template>
  </BaseChartPlotly>
</template>

<style scoped>
.faded {
  opacity: 0.3;
}
</style>
