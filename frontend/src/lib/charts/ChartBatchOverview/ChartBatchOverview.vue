<script setup>
import { ref, computed, watchEffect } from 'vue'

import ToggleSwitch from 'primevue/toggleswitch'
import Select from 'primevue/select'

import BaseChartPlotly from '../BaseChartPlotly.vue'

import { beautifySnakeCase } from '@/lib/utils'
import { useApp } from '@/stores'

import { useChartData } from './data'

const app = useApp()
const data = useChartData()

const log = ref(false)

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
    title: 'Intensity',
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
  // Select sample item corresponding to clicked data point
  let sampleItemIndex = points[0].pointIndex
  let sampleItem = app.data.sample.list[sampleItemIndex]
  if (sampleItem) {
    app.data.sample.focus(sampleItem)
  } else {
    app.data.sample.unfocus()
  }
}
</script>

<template>
  <figure>
    <div class="row">
      <Select
        v-model:modelValue="xField"
        :options="xFields"
        optionLabel="label"
        dataKey="field"
        style="z-index: 100"
        filter
      />
      <ToggleSwitch v-model="log" style="margin-left: 1rem" />
      <span> log scale </span>
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

<style scoped>
figure {
  position: relative;
}

.row {
  position: absolute;
  left: 1rem;
  top: 1rem;
}
</style>
