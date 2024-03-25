<script setup>
import { ref, computed } from 'vue'

import BaseChartPlotly from './BaseChartPlotly.vue'

import { glasbeyLight } from '@/lib/styles'

import { useBatchStore } from '@/stores'

const batchStore = useBatchStore()

const hovertemplate = `
  <b># %{x}</b>
  <br>
  <b>%{text}</b>
  <br>
  y: %{y:,.0f}
  <br>
  %{customdata}
`
const yAxisLog = ref(false)

const data = computed(() => {
  if (!(batchStore.sampleItems && batchStore.matchCompounds)) return []
  let allCompoundIds =
    batchStore.targetCompounds?.map((compound) => compound.target_compound_id) ?? []
  allCompoundIds = [...new Set(allCompoundIds)]
  let compoundColors = Object.fromEntries(
    allCompoundIds.map((compoundId, index) => [[compoundId], glasbeyLight[index]])
  )
  let data = []
  let x = batchStore.sampleItems?.map((item) => item.sample_item_id) ?? []

  // Loop through target compounds, make traces and push to data
  for (let targetCompoundId of allCompoundIds) {
    let y = []
    let compoundMaxMatchCategory
    for (let sampleItemId of x) {
      let itemMatches = batchStore.matchCompounds.filter(
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
    let compound = batchStore.targetCompounds.filter(
      (target) => target.target_compound_id === targetCompoundId
    )[0]
    data.push({
      name: compound.target_compound_name.trim()
        ? compound.target_compound_name
        : compound.target_compound_formula,
      target_compound_id: targetCompoundId,
      x,
      y,
      customdata: batchStore.sampleItems.map((item) => item.datetime),
      text: batchStore.sampleItems.map((item) => item.sample_item_name),
      hovertemplate,
      mode: 'markers',
      type: 'scatter',
      marker: {
        color: compoundColor, //`rgb(${compoundColor[0]},${compoundColor[1]},${compoundColor[2]})`,
        size: 10,
        symbol: compoundSymbol
      }
    })
  }
  // Make trace for TIC
  let y = batchStore.sampleItems?.map((item) => item.tic) ?? []
  data.push({
    name: 'TIC',
    x,
    y,
    customdata: batchStore.sampleItems?.map((item) => item.datetime) ?? [],
    text: batchStore.sampleItems?.map((item) => item.sample_item_name) ?? [],
    hovertemplate,
    mode: 'markers',
    type: 'scatter',
    marker: {
      color: 'white',
      size: 10,
      symbol: 'diamond'
    }
  })

  return data
})
const layout = computed(() => ({
  xaxis: {
    title: 'Sample item',
    autorange: true,
    showgrid: true,
    tickmode: 'array',
    tickvals: batchStore.sampleItems?.map((item) => item.sample_item_id) ?? [],
    ticktext: batchStore.sampleItems?.map((_, i) => i + 1) ?? [],
    gridcolor: '#464752',
    gridwidth: 1
  },
  yaxis: {
    title: 'Intensity',
    type: yAxisLog.value ? 'log' : 'lin',
    showgrid: true,
    autorange: true,
    rangemode: 'tozero',
    gridcolor: '#464752',
    gridwidth: 1
  },
  showlegend: true
}))

function itemSelect(row) {
  batchStore.itemToggle(row)
  batchStore.itemFocus(row)
}
function onClick(event) {
  // Select sample item corresponding to clicked data point
  let sampleItemIndex = event.points[0].pointIndex
  let sampleItem = batchStore.sampleItems[sampleItemIndex]
  itemSelect(sampleItem)
  // Mouse button dependent action
  switch (event.event.button) {
    case 0:
      // Left click
      break
    case 1:
      // Middle click
      break
    case 2:
      // Right click
      break
  }
}
</script>

<template>
  <div class="columns">
    <div class="column is-1">
      <br /><br /><br />
      <b-field>
        <template #label
          ><div style="text-align: center">
            <b-icon icon="math-log"></b-icon></div
        ></template>
        <b-switch v-model="yAxisLog"></b-switch>
      </b-field>
    </div>
    <div class="column is-11">
      <base-chart-plotly
        id="ChartSampleIntensity"
        :title="batchStore.active?.sample_batch_name ?? ''"
        :data="data"
        :layout="layout"
        @click="onClick"
      ></base-chart-plotly>
    </div>
  </div>
</template>
