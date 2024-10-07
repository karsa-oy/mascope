<script setup>
import { ref, computed, watchEffect } from 'vue'

import ToggleSwitch from 'primevue/toggleswitch'
import Select from 'primevue/select'
import Chip from 'primevue/chip'

import BaseChartPlotly from '../BaseChartPlotly.vue'

import { beautifySnakeCase } from '@/lib/utils'
import { useApp } from '@/stores'

import { useChartData } from './data'

const app = useApp()
const data = useChartData()

const log = ref(true)

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
  xField.value = xFields.value.find(({ field }) => field == 'index')
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
  tickvals: app.data.sample.list?.map((_, i) => i) ?? [],
  ticktext: app.data.sample.list?.map(toField(xField.value ?? 'index')) ?? []
}))

const layout = computed(() => ({
  xaxis: {
    title: xField.value?.label,
    autorange: true,
    showgrid: true,
    gridcolor: '#33333399',
    tickmode: 'array',
    gridwidth: 1,
    ...xAxis.value
  },
  yaxis: {
    title: 'Signal intensity [cps]',
    type: log.value ? 'log' : 'lin',
    showgrid: true,
    gridcolor: '#33333399',
    autorange: true,
    rangemode: 'tozero',
    gridwidth: 1
  },
  showlegend: true
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
</script>

<template>
  <figure>
    <div class="row" style="justify-content: space-between; width: 100%">
      <Select
        v-model:modelValue="xField"
        :options="xFields"
        optionLabel="label"
        dataKey="field"
        filter
      />
      <Chip
        v-if="app.ui.filter.mechanism"
        icon="pi pi-filter"
        :label="app.ui.filter.mechanism.ionization_mechanism"
        removable
        @remove="app.ui.filter.mechanism = null"
      />
      <div class="row">
        <ToggleSwitch v-model="log" style="margin-left: 1rem" />
        <span> log scale </span>
      </div>
    </div>
    <BaseChartPlotly
      id="ChartSampleIntensity"
      :title="app.data.batch.focused.sample_batch_name ?? ''"
      :data="data.traces"
      :layout="layout"
      @click="onClick"
    />
  </figure>
</template>
