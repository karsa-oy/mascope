<script setup>
import { ref, computed, watch, toRaw } from 'vue'

import Select from 'primevue/select'
import FloatLabel from 'primevue/floatlabel'
import Chip from 'primevue/chip'

import { useApp } from '@/stores'
import { ToolbarIntensityScale } from '@/lib/toolbars'

import BaseChartPlotly from '../BaseChartPlotly.vue'
import { useChartData } from './data'

const app = useApp()
const data = useChartData()

const scale = ref({
  mode: 'average',
  max: null,
  log: true
})

const unit = computed(() =>
  // Adjust the y-axis unit based on "average / sum" toggle
  scale.value.mode == 'average' ? '[cps]' : '[counts]'
)

const traces = computed(() => {
  // Scale trace y-values based on "sum / average" toggle
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

const num = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
})
const score = new Intl.NumberFormat('en-US', {
  style: 'percent',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
})
const toField =
  ({ field, type }) =>
  (item) => {
    let value
    if (field in item) {
      value = item[field]
    } else if (field in item.sample_item_attributes) {
      value = item.sample_item_attributes[field]
    } else {
      value = 'NA'
    }
    let formatted
    switch (field) {
      case 'match_score':
        formatted = score.format(value)
        break
      case 'matched':
        formatted = value > 0.5 ? 'true' : 'false'
        break
      case 'time':
        formatted = item['datetime'].split('T')[1].split('.')[0]
        break
      default:
        formatted = type == 'number' ? num.format(value) : value
    }
    return formatted
  }
const xAxis = computed(() => ({
  // Do not display dummy date for 'Time of day' x-axis, default for others
  tickformat: data.xField.field == 'time_of_day' ? '%H:%M:%S' : undefined
}))

const rangeY = computed(() =>
  scale.value.max && scale.value.max > 0 ? { range: [0, scale.value.max] } : { autorange: true }
)

const layout = computed(() => ({
  xaxis: {
    title: { text: data.xField?.label },
    autorange: true,
    automargin: true,
    showgrid: true,
    gridcolor: '#33333399',
    tickmode: 'array',
    tickangle: 45,
    gridwidth: 1,
    ...xAxis.value
  },
  yaxis: {
    title: { text: `Intensity ${unit.value}` },
    type: scale.value.log ? 'log' : 'lin',
    showgrid: true,
    gridcolor: '#33333399',
    rangemode: 'tozero',
    gridwidth: 1,
    ...rangeY.value
  },
  margin: { l: 50, r: 50, t: 50, b: 50 },
  showlegend: true,
  autosize: true
}))

function onClick({ pointIndex, curveNumber }) {
  if (pointIndex == null || curveNumber == null) return
  // Select sample corresponding to the clicked data point
  const sample = app.data.sample.list[pointIndex]

  watch(
    () => app.data.match.ion.list,
    (list) => {
      // Focus on the corresponding compound/ion using the trace index
      const trace = data.traces[curveNumber]
      // Guard for matchData availability
      if (!trace.matchData) {
        return
      }
      const { level, match_key } = trace.matchData
      if (level && level === 'compound') {
        app.data.match.compound.focus({ match_key })
      } else if (level && level === 'ion') {
        app.data.match.ion.focus({ match_key })
      }
    },
    { once: true }
  )

  if (sample) {
    app.data.sample.focus(sample)
  } else {
    app.data.sample.unfocus()
  }
}

const anyFilters = computed(
  () =>
    app.ui.filter.collections.length ||
    app.ui.filter.mechanism ||
    app.data.sample.selected.length > 1
)
</script>

<template>
  <figure style="height: calc(100vh - 200px)">
    <div
      class="row"
      :style="`
        justify-content: flex-start;
        width: calc(${app.ui.split.right}vw - 3rem);
        position: fixed;
        top: 10rem;
        z-index: 100
      `"
    >
      <span v-if="anyFilters" class="pi pi-filter" style="opacity: 0.5" />
      <Chip
        v-for="coll in app.ui.filter.collections"
        icon="pi pi-bullseye"
        :label="coll.target_collection_name"
        removable
        @remove="
          app.ui.filter.collections = app.ui.filter.collections.filter(
            ({ target_collection_id }) => target_collection_id !== coll.target_collection_id
          )
        "
        :key="coll.target_collection_id"
      />
      <Chip
        v-if="app.ui.filter.mechanism"
        icon="pi pi-cog"
        :label="app.ui.filter.mechanism.ionization_mechanism"
        removable
        @remove="app.ui.filter.mechanism = null"
      />
    </div>
    <BaseChartPlotly
      id="ChartSampleIntensity"
      :title="app.data.batch.focused.sample_batch_name ?? ''"
      :data="traces"
      :layout="layout"
      @click="onClick"
    >
      <template v-slot:settings>
        <ToolbarIntensityScale v-model="scale" />
        <div style="height: 0.5rem" />
        <FloatLabel>
          <Select
            v-model:modelValue="data.xField"
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
