<script setup>
import { ref, computed, watch, toRaw, onUnmounted } from 'vue'

import Select from 'primevue/select'
import FloatLabel from 'primevue/floatlabel'
import ProgressSpinner from 'primevue/progressspinner'

import { useApp } from '@/stores'
import { ToolbarIntensityScale } from '@/lib/toolbars'

import BaseChartPlotly from '../BaseChartPlotly.vue'
import { useSampleScroller } from '@/lib/panes/PaneBrowserSample/stores'
import { useChartData } from './data'

const app = useApp()
const data = useChartData()
const scroller = useSampleScroller()

const plot = ref({})
const showSpinner = ref(false)

const scale = ref({
  mode: 'average',
  max: null,
  log: true
})

const chartTitle = computed(() => {
  const batchName = app.data.batch?.focused?.sample_batch_name || null
  const sampleCount = app.data.sample?.list.length || 0

  if (!batchName) return ''

  return `${batchName} <i>(${sampleCount} samples)</i>`
})

const chartSubtitle = computed(() => {
  if (!app.data.match.collection.focused) return 'Select a target collection to visualize matches'
  return `Collection: ${app.data.match.collection.focused.target_collection_name}`
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
  tickformat: data.xField?.field === 'time_of_day' ? '%H:%M:%S' : undefined
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
    // Scroll to sample in table
    scroller.scrollToSample(app.data.sample.focusedId)
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
  // Scroll to first selected sample in table
  scroller.scrollToSamples(app.data.sample.selectedIds)
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

let loadingTimeout = null
watch(
  () => app.data.match.batch_overview.pending,
  (isLoading) => {
    if (loadingTimeout) {
      clearTimeout(loadingTimeout)
      loadingTimeout = null
    }

    if (isLoading) {
      loadingTimeout = setTimeout(() => {
        showSpinner.value = true
      }, 300)
    } else {
      showSpinner.value = false
    }
  },
  { immediate: true }
)

onUnmounted(() => {
  if (loadingTimeout) clearTimeout(loadingTimeout)
})
</script>

<template>
  <figure style="height: calc(100vh - 200px)">
    <div v-if="showSpinner" class="spinner">
      <div>
        <ProgressSpinner strokeWidth="5px" />
      </div>
    </div>
    <BaseChartPlotly
      v-else
      id="ChartSampleIntensity"
      ref="plot"
      :title="chartTitle"
      :subtitle="chartSubtitle"
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

<style scoped>
.spinner :deep(.p-progressspinner) {
  height: auto !important;
  width: 50px !important;
  height: 50px !important;
  opacity: 0.8;
}
</style>
