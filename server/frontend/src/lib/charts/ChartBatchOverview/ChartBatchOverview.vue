<script setup>
import { ref, computed, watch, toRaw } from 'vue'

import Select from 'primevue/select'
import FloatLabel from 'primevue/floatlabel'

import { useApp } from '@/stores'
import { ToolbarIntensityScale } from '@/lib/toolbars'

import BaseChartPlotly from '../BaseChartPlotly.vue'
import { useChartData } from './data'

const app = useApp()
const data = useChartData()

const plot = ref({})

const chartTitle = computed(() =>
  app.data.batch.focused.sample_batch_name
    ? `${app.data.batch.focused.sample_batch_name} <i>(${app.data.sample.list.length} samples)</i>`
    : ''
)

const scale = ref({
  mode: 'average',
  max: null,
  log: true
})

const unit = computed(() =>
  // Adjust the y-axis unit based on "average / sum" toggle
  scale.value.mode == 'average' ? '[cps]' : '[counts]'
)

/**
 * Scale traces based on average/sum mode
 */
const traces = computed(() => {
  if (!data.traces.length) return []

  // Collect sample lengths into an object {[sample_item_id]: sample.length}
  const sampleLengths = app.data.sample.list.reduce(
    (o, sample) => ({ ...o, [sample.sample_item_id]: sample.length }),
    {}
  )
  return scale.value.mode == 'average'
    ? data.traces.map((trace) => {
        let newTrace = structuredClone(toRaw(trace))
        newTrace.customdata = trace.customdata.map((cd) => [cd[0], 'counts/s'])
        return newTrace
      })
    : data.traces.map((trace) => {
        // Scale chart traces by dividing all y-values by sampleLength
        let newTrace = structuredClone(toRaw(trace))
        // Use x-coordinate (sample_item_id) to retrieve sample length
        newTrace.y = trace.y.map((value, i) =>
          value !== null ? value * sampleLengths[app.data.sample.list[i].sample_item_id] : null
        )
        // Unit is in the second element of customdata. Append with "counts"
        newTrace.customdata = trace.customdata.map((cd) => [cd[0], 'counts'])
        return newTrace
      })
})

const xAxis = computed(() => ({
  // Do not display dummy date for 'Time of day' x-axis, default for others
  tickformat: data.xField.field === 'time_of_day' ? '%H:%M:%S' : undefined
}))

const dragmode = ref('zoom')

const zoom = {
  rangeX: null,
  rangeY: null
}

const layout = computed(() => {
  const scaleRangeY =
    scale.value.max && scale.value.max > 0
      ? { range: [0, scale.value.max], autorange: false }
      : null

  const autorange = { range: null, autorange: true }
  const yRange = scaleRangeY
    ? { ...scaleRangeY, autorange: false }
    : zoom.rangeY
      ? { ...zoom.rangeY, autorange: false }
      : autorange
  const xRange = zoom.rangeX ? { ...zoom.rangeX, autorange: false } : autorange

  return {
    xaxis: {
      title: { text: data.xField?.label },
      autorange: true,
      automargin: true,
      showgrid: true,
      gridcolor: '#33333399',
      tickmode: 'array',
      tickangle: 45,
      gridwidth: 1,
      ...xAxis.value,
      ...xRange
    },
    yaxis: {
      title: { text: `Intensity ${unit.value}` },
      type: scale.value.log ? 'log' : 'lin',
      showgrid: true,
      gridcolor: '#33333399',
      rangemode: 'tozero',
      gridwidth: 1,
      ...yRange
    },
    margin: { l: 50, r: 50, t: 50, b: 50 },
    showlegend: true,
    autosize: true,
    dragmode: dragmode.value
  }
})

/**
 * Handle click on chart point - focus sample and ion directly
 */
function onClick({ pointIndex, curveNumber }) {
  if (pointIndex == null || curveNumber == null) return

  // Focus sample corresponding to the clicked data point
  const sample = app.data.sample.list[pointIndex]
  if (sample) {
    app.data.sample.focus(sample)
  } else {
    app.data.sample.unfocus()
  }

  // Focus on the corresponding ion using the trace index
  const trace = data.traces[curveNumber]
  if (!trace?.matchData) return

  const { target_ion_id } = trace.matchData

  // Focus in match.ion store by target_ion_id
  if (target_ion_id) {
    app.data.match.ion.focus({ target_ion_id })
  }
}

/**
 * Handle selection on chart - update sample selection
 */
function onSelect({ points }) {
  const samples = points.map((i) => app.data.sample.list[i])
  app.data.sample.selected = samples
}

/**
 * Sync chart selection with sample selection
 */
watch(
  () => app.data.sample.selected,
  (selected) => {
    if (!plot.value) return

    if (selected.length <= 0) {
      plot.value.resetSelection()
    } else {
      // Select samples in the chart
      const pointIndices = selected.map((sample) => app.data.sample.list.indexOf(sample))
      plot.value?.selectPoints(pointIndices)
    }
  }
)
</script>

<template>
  <figure style="height: calc(100vh - 200px)">
    <BaseChartPlotly
      id="ChartSampleIntensity"
      ref="plot"
      :title="chartTitle"
      :data="traces"
      :layout="layout"
      @click="onClick"
      @dragmode="
        (mode) => {
          dragmode = mode
        }
      "
      @select="onSelect"
      @zoom="
        ({ rangeX, rangeY }) => {
          zoom.rangeX = rangeX ?? zoom.rangeX
          zoom.rangeY = rangeY ?? zoom.rangeY
        }
      "
    >
      <template v-slot:settings>
        <ToolbarIntensityScale v-model="scale" />
        <div style="height: 0.5rem" />
        <FloatLabel>
          <Select
            v-model="data.xField"
            :options="data.xFields"
            optionLabel="label"
            dataKey="field"
            filter
            fluid
          />
          <label>X-axis</label>
        </FloatLabel>
      </template>
    </BaseChartPlotly>
  </figure>
</template>
