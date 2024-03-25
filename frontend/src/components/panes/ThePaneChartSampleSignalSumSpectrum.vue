<script setup>
import { ref, computed } from 'vue'

import BaseChartPlotly from '@/components/base/BaseChartPlotly.vue'

import { useVisualizationStore } from '@/stores'

const visualizationStore = useVisualizationStore()

const yAxisMax = ref(null)

const layout = computed(() => {
  if (!visualizationStore.tracesSignalSumSpectrum) return {}

  const annotations = visualizationStore.activeIsotopes
    .map((isotope) => {
      if (isotope.sample_peak_area === 0) return null

      // Find the trace that corresponds to the isotope in focus
      const correspondingTrace = visualizationStore.tracesSignalSumSpectrum.find(
        (trace) => trace.target_isotope_id === isotope.target_isotope_id
      )
      if (!correspondingTrace) return null

      // Calculate the center position for the x-axis
      const xValues = correspondingTrace.x
      const xCenter = xValues.length > 0 ? (Math.max(...xValues) + Math.min(...xValues)) / 2 : 0

      return {
        text: `Target isotope intensity: ${formatNumber(isotope.sample_peak_area.toFixed(0))}`,
        x: xCenter,
        xref: 'x' + (correspondingTrace.xaxis === 'x' ? '' : '2'),
        xanchor: 'center',
        y: 1.06,
        yref: 'paper',
        yanchor: 'bottom',
        font: { size: 14 },
        showarrow: false
      }
    })
    .filter((annotation) => annotation !== null)

  return {
    grid: {
      rows: 1,
      columns: 2,
      pattern: 'independent'
    },
    yaxis: yAxisConfiguration.value,
    xaxis: xAxisConfiguration.value,
    yaxis2: yAxisConfiguration.value,
    xaxis2: xAxisConfiguration.value,
    dragmode: 'zoom',
    showlegend: false,
    height: '400',
    width: '860',
    annotations: annotations
  }
})
const xAxisConfiguration = computed(() => {
  return {
    title: 'm/z [Th]',
    gridcolor: '#464752',
    gridwidth: 1
  }
})
const yAxisConfiguration = computed(() => {
  let yAxisConfig = {
    title: 'Signal intensity [cps]',
    gridcolor: '#464752',
    gridwidth: 1
  }
  if (yAxisMax.value !== null) {
    yAxisConfig.range = [0, yAxisMax.value]
  }
  return yAxisConfig
})

function formatNumber(value) {
  const roundedValue = Math.round(value)
  const formatter = new Intl.NumberFormat('en-US')
  return formatter.format(roundedValue)
}
</script>

<template>
  <div style="position: relative">
    <div class="intensity-container">
      <b-field>
        <b-input
          class="intensity-input"
          v-model="yAxisMax"
          placeholder="Set intensity scale"
        ></b-input>
      </b-field>
    </div>
    <base-chart-plotly
      id="ChartSampleSignalSumSpectrum"
      title="Sum spectrum"
      :data="visualizationStore.tracesSignalSumSpectrum"
      :layout="layout"
    ></base-chart-plotly>
  </div>
</template>
