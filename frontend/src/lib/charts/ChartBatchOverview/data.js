import { ref, computed, watchEffect } from 'vue'
import { defineStore } from 'pinia'

import { api } from '@/api/client.js'
import { useApp } from '@/stores'

import { glasbey } from '../colors.js'

export const useChartData = defineStore('chart.batch.overview', () => {
  const app = useApp()

  const traces = ref([])
  const theme = computed(() => (app.ui.darkmode.active ? glasbey.dark : glasbey.light))
  const hovertemplate = `
    <b># %{x}</b>
    <br>
    <b>%{text}</b>
    <br>
    y: %{y:,.0f}
    <br>
    %{customdata}
    `

  const load = async (sample_batch_id) => {
    traces.value = []

    let compounds
    try {
      compounds = (
        await api.client.get(`/match/compounds`, {
          params: {
            sample_batch_id,
            show_target_compound: true
          }
        })
      )?.data?.data
    } catch (error) {
      throw new Error(`chart.batch.overview - failed to load match compounds: ${error}`)
    }

    let compoundIds = [...new Set(compounds.map((compound) => compound.target_compound_id) ?? [])]
    let colors = Object.fromEntries(
      compoundIds.map((compoundId, index) => [[compoundId], theme.value[index]])
    )

    let x = app.data.sample.list?.map((item) => item.sample_item_id) ?? []

    // Loop through target compounds, make traces and push to data
    for (let compoundId of compoundIds) {
      let y = []
      let compoundMaxMatchCategory
      for (let sampleId of x) {
        let itemMatches = compounds.filter((row) => row.sample_item_id === sampleId)
        let sampleItemCompoundStats = itemMatches
          .filter((match) => match.target_compound_id === compoundId)
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
      let color = colors[compoundId]
      let compound = compounds.filter((target) => target.target_compound_id === compoundId)[0]
      traces.value.push({
        name: compound.target_compound_name.trim()
          ? compound.target_compound_name
          : compound.target_compound_formula,
        target_compound_id: compoundId,
        x,
        y,
        customdata: app.data.sample.list.map((item) => item.datetime),
        text: app.data.sample.list.map((item) => item.sample_item_name),
        hovertemplate,
        mode: 'markers',
        type: 'scatter',
        marker: {
          color,
          size: 10,
          symbol: compoundSymbol
        }
      })
    }
    // Make trace for TIC
    let y = app.data.sample.list?.map((item) => item.tic) ?? []
    traces.value.push({
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
  }
  watchEffect(async () => {
    const batchId = app.data.batch.focused?.sample_batch_id
    if (batchId) {
      await load(batchId)
    }
  })

  return {
    traces
  }
})
