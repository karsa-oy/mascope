<script setup>
import { ref, computed, watchEffect, toRaw } from 'vue'

import SelectButton from 'primevue/selectbutton'
import ToggleSwitch from 'primevue/toggleswitch'
import Select from 'primevue/select'
import Chip from 'primevue/chip'

import { beautifySnakeCase } from '@/lib/utils'
import { useApp } from '@/stores'

import BaseChartPlotly from '../BaseChartPlotly.vue'
import { useChartData } from './data'

const app = useApp()
const data = useChartData()

const yMode = ref('average')
const log = ref(true)
const unit = computed(() =>
  // Adjust the y-axis unit based on "average / sum" toggle
  yMode.value == 'average' ? 'Counts per second' : 'Counts'
)

const traces = computed(() => {
  // Scale trace y-values based on "sum / average" toggle
  // Collect sample lengths into an object {[sample_item_id]: sample.length}
  const sampleLengths = app.data.sample.list.reduce(
    (o, sample) => ({ ...o, [sample.sample_item_id]: sample.length }),
    {}
  )
  return yMode.value == 'average'
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
          value !== null ? value * sampleLengths[trace.x[i]] : null
        )
        // Unit is in the second element of customdata. Append with "counts"
        newTrace.customdata = trace.customdata.map((cd) => [cd[0], 'counts'])
        return newTrace
      })
})

const inferType = (field) => {
  const withField = app.data.sample.list.filter((item) => field in item)
  const types = [
    ...new Set(withField.map((item) => (item[field] ? typeof item[field] : 'null')))
  ].filter((type) => type !== 'null')
  return types.length == 1 ? types[0] : 'unknown'
}
const xFields = computed(() => {
  const standard = [
    ...new Set(
      app.data.sample.list
        ?.map((item) => Object.keys(item ?? {}))
        .flat()
        .filter((field) => field !== 'sample_item_attributes')
    )
  ].map((field) => ({ field, kind: 'standard' }))
  const custom = [
    ...new Set(
      app.data.sample.list?.map((item) => Object.keys(item?.sample_item_attributes ?? {})).flat()
    )
  ].map((field) => ({ field, kind: 'custom' }))
  return [...standard, { field: 'time', kind: 'custom', label: 'Time' }, ...custom]
    .map(({ field, kind }) => ({
      field,
      kind,
      label: beautifySnakeCase(field),
      type: kind == 'custom' ? 'string' : inferType(field)
    }))
    .filter(({ type }) => type !== 'object')
})
const xField = ref()

watchEffect(() => {
  xField.value = xFields.value.find(({ field }) => field == 'sample_item_name')
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
  tickvals: data.samples.map((_, i) => i),
  ticktext: data.samples.map(toField(xField.value ?? 'index'))
}))

const layout = computed(() => ({
  xaxis: {
    title: xField.value?.label,
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
    title: `Intensity ${unit.value}`,
    type: log.value ? 'log' : 'lin',
    showgrid: true,
    gridcolor: '#33333399',
    autorange: true,
    rangemode: 'tozero',
    gridwidth: 1
  },
  margin: { l: 50, r: 50, t: 50, b: 50 },
  minreducedheight: 300,
  showlegend: true,
  height: 650
}))

function onClick({ points }) {
  if (!points) return
  // Select sample corresponding to the clicked data point
  const sampleIndex = points[0].pointIndex
  const sample = app.data.sample.list[sampleIndex]

  if (sample) {
    app.data.sample.focus(sample)
  } else {
    app.data.sample.unfocus()
  }

  // Focus on the corresponding compound/ion using the trace index
  const traceIndex = points[0].curveNumber
  const trace = data.traces[traceIndex]

  // Guard for matchData availability
  if (!trace.matchData) return

  const { level, match_key } = trace.matchData
  if (level && level === 'compound') {
    app.data.match.compound.focus({ match_key })
  } else if (level && level === 'ion') {
    app.data.match.ion.focus({ match_key })
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
  <figure>
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
      <Chip
        v-if="app.data.sample.selected.length > 1"
        icon="pi pi-tags"
        :label="`${app.data.sample.selected.length} samples`"
        removable
        @remove="app.data.sample.unfocus()"
      />
    </div>
    <BaseChartPlotly
      id="ChartSampleIntensity"
      :title="app.data.batch.focused.sample_batch_name ?? ''"
      :data="traces"
      :layout="layout"
      @click="onClick"
    />
  </figure>
  <div
    class="row"
    :style="`
      justify-content: space-between;
      width: calc(${app.ui.split.right}vw - 6rem);
      position: fixed;
      bottom: 35px;
      right: 2rem;
    `"
  >
    <div class="row">
      <SelectButton v-model="yMode" :options="['average', 'sum']" />
      <ToggleSwitch v-model="log" style="margin-left: 1rem" />
      <span> log scale </span>
    </div>
    <Select
      v-model:modelValue="xField"
      :options="xFields"
      optionLabel="label"
      dataKey="field"
      filter
    />
  </div>
</template>
