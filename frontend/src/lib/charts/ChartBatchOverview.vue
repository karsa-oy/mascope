<script setup>
import { ref, computed, watchEffect } from 'vue'

import ToggleSwitch from 'primevue/toggleswitch'
import Select from 'primevue/select'

import BaseChartPlotly from './BaseChartPlotly.vue'

import { glasbey } from './colors.js'

import { beautifySnakeCase } from '@/lib/utils'
import { useApp } from '@/stores'

const app = useApp()

const swatches = computed(() => (app.ui.darkmode.active ? glasbey.dark : glasbey.light))

const hovertemplate = `
  <b># %{x}</b>
  <br>
  <b>%{text}</b>
  <br>
  y: %{y:,.0f}
  <br>
  %{customdata}
`
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

const chartData = computed(() => {
  if (!(app.data.sample.list && app.data.match.compound.list)) return []
  let allCompoundIds =
    app.data.match.compound.list.map((compound) => compound.target_compound_id) ?? []
  allCompoundIds = [...new Set(allCompoundIds)]
  let compoundColors = Object.fromEntries(
    allCompoundIds.map((compoundId, index) => [[compoundId], swatches.value[index]])
  )
  let traces = []
  let x = app.data.sample.list?.map((item) => item.sample_item_id) ?? []

  // Loop through target compounds, make traces and push to data
  for (let targetCompoundId of allCompoundIds) {
    let y = []
    let compoundMaxMatchCategory
    for (let sampleItemId of x) {
      let itemMatches = app.data.match.compound.list.filter(
        (row) => row.sample_item_id === sampleItemId
      )
      let sampleItemCompoundStats = itemMatches
        .filter((match) => match.target_compound_id === targetCompoundId)
        .map((compoundMatch) =>
          Object.fromEntries([
            ['match_category', compoundMatch.match_category],
            ['intensity', compoundMatch.sample_peak_area_sum]
          ])
        )[0]
      if (sampleItemCompoundStats) {
        y.push(
          sampleItemCompoundStats.match_category > 0 ? sampleItemCompoundStats.intensity : null
        )
      } else {
        y.push(null)
      }
      compoundMaxMatchCategory = sampleItemCompoundStats?.match_category || 0
    }
    if (y.every((intensity) => intensity === null)) continue
    let compoundSymbol = compoundMaxMatchCategory === 2 ? 'square' : 'square-open'
    let compoundColor = compoundColors[targetCompoundId]
    let compound = app.data.match.compound.list.filter(
      (target) => target.target_compound_id === targetCompoundId
    )[0]
    traces.push({
      name: compound.target_compound_name.trim()
        ? compound.target_compound_name
        : compound.target_compound_formula,
      target_compound_id: targetCompoundId,
      x,
      y,
      customdata: app.data.sample.list.map((item) => item.datetime),
      text: app.data.sample.list.map((item) => item.sample_item_name),
      hovertemplate,
      mode: 'markers',
      type: 'scatter',
      marker: {
        color: compoundColor,
        size: 10,
        symbol: compoundSymbol
      }
    })
  }
  // Make trace for TIC
  let y = app.data.sample.list?.map((item) => item.tic) ?? []
  traces.push({
    name: 'TIC',
    x,
    y,
    customdata: app.data.sample.list?.map((item) => item.datetime) ?? [],
    text: app.data.sample.list?.map((item) => item.sample_item_name) ?? [],
    hovertemplate,
    mode: 'markers',
    type: 'scatter',
    marker: {
      color: app.ui.darkmode.active ? '#fff' : '#222',
      size: 10,
      symbol: 'diamond'
    }
  })

  return traces
})

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
      :data="chartData"
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
