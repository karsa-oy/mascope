<script setup>
import { ref, computed, toRaw } from 'vue'

import SelectButton from 'primevue/selectbutton'
import ToggleSwitch from 'primevue/toggleswitch'
import ProgressSpinner from 'primevue/progressspinner'

import { BaseParamField } from '@/lib/base'
import { useApp } from '@/stores'

import BaseChartPlotly from '../BaseChartPlotly.vue'
import { useChartData } from './data.js'

const app = useApp()
const data = useChartData()

const yMode = ref('average')
const scale = ref()
const log = ref()
const unit = computed(() =>
  // Adjust the y-axis unit based on "average / sum" toggle
  yMode.value == 'average' ? 'counts/s' : 'counts'
)

const traces = computed(() => {
  // Scale trace y-values based on "sum / average" toggle
  if (app.data.sample.selected.length != 1) {
    return []
  }
  const sampleLength = app.data.sample.selected[0].length
  return yMode.value == 'average'
    ? data.traces
    : data.traces.map((trace) => {
        // Scale chart traces by dividing all y-values by sampleLength
        let newTrace = structuredClone(toRaw(trace))
        newTrace.y = trace.y.map((value) => value * sampleLength)
        // For peak traces, scale "customdata" containing [height, area]
        if (newTrace.name == 'Peak') {
          newTrace.customdata = trace.customdata.map((subarr) => {
            return subarr.map((value) => value * sampleLength)
          })
        }
        return newTrace
      })
})

const layout = computed(() => ({
  xaxis: {
    title: 'm/z [Th]',
    autorange: true,
    showgrid: true,
    gridcolor: '#33333399',
    gridwidth: 1
  },
  yaxis: {
    title: `Signal intensity [${unit.value}]`,
    showgrid: true,
    rangemode: 'nonnegative',
    gridcolor: '#33333399',
    gridwidth: 1,
    type: log.value ? 'log' : 'lin',
    ...(scale.value
      ? { range: [0, scale.value] }
      : {
          autorange: true
        })
  },
  dragmode: 'zoom',
  showlegend: false
}))

const config = {
  modeBarButtonsToRemove: ['autoScale', 'resetScale2d', 'pan2d']
}
</script>

<template>
  <figure style="position: relative" :class="data.loading ? 'faded' : ''">
    <div
      style="
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        min-height: 100%;
        z-index: 100;
        display: grid;
        place-items: center;
      "
      v-if="data.loading"
    >
      <ProgressSpinner />
    </div>
    <BaseChartPlotly
      id="ChartSampleSpectrum"
      title="Spectrum"
      :data="traces"
      :layout="layout"
      :config="config"
    />
  </figure>
  <div
    class="row"
    :style="`
      justify-content: space-between;
      width: calc(${app.ui.split.right}vw - 4rem);
      position: absolute;
      bottom: 35px;
      right: 2rem;
    `"
  >
    <div class="row">
      <SelectButton v-model="yMode" :options="['average', 'sum']" />
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
</template>

<style scoped>
.faded {
  opacity: 0.3;
}
</style>
