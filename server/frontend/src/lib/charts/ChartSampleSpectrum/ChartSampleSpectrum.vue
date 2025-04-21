<script setup>
import { ref, reactive, computed, toRaw, watch, watchEffect } from 'vue'

import SelectButton from 'primevue/selectbutton'
import ToggleSwitch from 'primevue/toggleswitch'
import ProgressSpinner from 'primevue/progressspinner'

import { BaseParamField } from '@/lib/base'
import { useApp } from '@/stores'
import { usePreview } from '@/lib/panes'

import BaseChartPlotly from '../BaseChartPlotly.vue'
import { useChartData } from './data.js'

const app = useApp()
const data = useChartData()

const preview = usePreview()

const yMode = ref('average')
const scale = ref()
const log = ref()
const peakAssign = reactive({
  dialog: false,
  mz: null
})

const unit = computed(() =>
  // Adjust the y-axis unit based on "average / sum" toggle
  yMode.value == 'average' ? 'counts/s' : 'counts'
)
const sampleLength = computed(() => app.data.sample.focused.length) // duration in seconds

const traces = computed(() =>
  yMode.value === 'average'
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

watch([yMode, log], () => {
  zoom.rangeY = { autorange: true }
})

watchEffect(() => {
  if (app.data.peak.focused) {
    const mz = preview.peak?.mz ?? app.data.peak.focused.mz
    const factor = yMode.value == 'sum' ? sampleLength.value : 1
    const height = preview.peak
      ? factor * data.mzRangeMax(mz, 0.3)
      : factor * Math.max(app.data.peak.focused.height, data.mzRangeMax(mz, 0.3))
    zoom.rangeX = { range: [mz - 0.3, mz + 0.3] }
    zoom.rangeY = log.value ? { autorange: true } : { range: [0, height * 1.2] }
  } else {
    zoom.rangeX = null
    zoom.rangeY = null
  }
})

const layout = computed(() => {
  const scaleRangeY = scale.value && scale.value > 0 ? { range: [0, scale.value] } : null
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
      type: log.value ? 'log' : 'lin',
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
  <div class="col" style="gap: 0.5rem; height: 450px; width: 100%">
    <div style="flex-grow: 1" class="center">
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
      />
    </div>
    <div class="row" style="width: 100%">
      <div class="row">
        <SelectButton v-model="yMode" :options="['average', 'sum']" :allowEmpty="false" />
        <ToggleSwitch v-model="log" />
        <span> log scale </span>
      </div>
      <BaseParamField
        label="Intensity scale"
        v-model:param="scale"
        :range="{ min: 0, max: 100000, step: 2000 }"
        hideSlider
      />
    </div>
  </div>
</template>

<style scoped>
.faded {
  opacity: 0.3;
}
</style>
