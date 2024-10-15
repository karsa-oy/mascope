import { ref, computed, watchEffect, onMounted, toRaw } from 'vue'
import { defineStore } from 'pinia'
import { api } from '@/api/client.js'
import { useApp } from '@/stores'
import { glasbey } from '../colors.js'

export const useChartData = defineStore('chart.batch.overview', () => {
  const app = useApp()
  const theme = computed(() => (app.ui.darkmode.active ? glasbey.dark : glasbey.light))

  const batch = ref(null)
  const match = ref({
    level: null,
    data: null
  })

  // Listen for `sample_batch_reload` event and reload data
  onMounted(() => {
    api.socket.on('sample_batch_reload', async () => {
      if (app.data.batch.focused) {
        // force reload by ensuring reactivity change
        batch.value = null
        batch.value = app.data.batch.focused
      }
    })
  })

  /**
   * Select batch to visualize based on specific requirements
   *
   * @watch
   * @param {[number|null, Array]} newValues - The new values of the watched sources.
   *   - `newValues[0]` (`batchId`): The currently selected batch ID.
   *   - `newValues[1]` (`sampleList`): The current list of loaded samples.
   */
  watchEffect(async () => {
    // requirements
    const batchFocused = app.data.batch.focused
    const samplesExist = app.data.sample.list?.length
    const samplesReady = app.data.sample.list?.every(
      (sample) => sample.sample_batch_id === batchFocused?.sample_batch_id
    )
    // either load or unload, based on requirements
    if (!batchFocused || !samplesExist || !samplesReady) {
      // unload chart if any dependency is unmet
      batch.value = null
      return
    } else {
      // load the chart if all requirements are met
      batch.value = batchFocused
    }
  })

  /**
   * Load match data for the visualized batch, using filters if they exist
   */
  watchEffect(() => {
    if (!batch.value) {
      return
    }
    const filters = app.ui.filter.mechanism ? { mechanism: app.ui.filter.mechanism } : null

    let data, level, queryParams
    if (!filters) {
      level = 'compound'
      queryParams = {
        deduplicate: true,
        show_target_collection: true,
        show_target_compound: true,
        sort: 'match_compound_utc_created',
        order: 'desc'
      }
    } else {
      level = 'ion'
      queryParams = {
        ionization_mechanism_id: filters.mechanism.ionization_mechanism_id,
        deduplicate: true,
        show_target_collection: true,
        show_target_compound: true,
        show_target_ion: true,
        show_ionization_mechanism: true,
        sort: 'match_ion_utc_created',
        order: 'desc'
      }
    }
    try {
      // API call includes filter for match_category (1 and 2 only)
      api.client
        .get(`/match/${level}s`, {
          params: {
            sample_batch_id: batch.value.sample_batch_id,
            match_category_min: 1,
            ...queryParams
          }
        })
        .then((response) => {
          data = response?.data?.data
          match.value = { data, level }
        })
    } catch (error) {
      throw new Error(`chart.batch.overview - failed to load match ${level}s: ${error}`)
    }
  })
  /**
   * Filter samples based on selection
   */
  const samples = computed(
    () =>
      app.data.sample.selected.length > 1 // if multiselecting
        ? app.data.sample.selected // filter chart to selection
        : (app.data.sample.list ?? []) // otherwise show everything
  )
  /**
   * Render visualization traces based on match data
   */
  const rawTraces = computed(() => {
    if (!match.value || !match.value?.data || !match.value?.data.length) {
      return []
    }
    const { data, level } = toRaw(match.value)
    const result = []
    //  Generate color mapping for target compounds
    const targetIds = [...new Set(data.map((match) => match[`target_${level}_id`]) ?? [])]
    const colors = Object.fromEntries(
      targetIds.map((targetId, index) => [[targetId], theme.value[index]])
    )

    // X-axis data: sample IDs
    const sampleIds = samples.value.map((sample) => sample.sample_item_id)

    // Loop through filtered target compounds and make traces
    for (let targetId of targetIds) {
      // Y-axis data: intensities (sample_peak_area_sum)
      const intensities = []
      let matchMaxMatchCategory = 1 // Start with minimum match category

      for (let sampleId of sampleIds) {
        let itemMatches = data.filter((row) => row.sample_item_id === sampleId)
        let sampleStats = itemMatches
          .filter((match) => match[`target_${level}_id`] === targetId)
          .map((compoundMatch) => ({
            match_category: compoundMatch.match_category,
            intensity: compoundMatch.sample_peak_area_sum
          }))[0]

        if (sampleStats) {
          intensities.push(sampleStats.match_category > 0 ? sampleStats.intensity : null)
          // Update the maximum match category for this compound
          if (sampleStats.match_category > matchMaxMatchCategory) {
            matchMaxMatchCategory = sampleStats.match_category
          }
        } else {
          intensities.push(null)
        }
      }

      // Skip if no valid intensity data
      if (intensities.every((intensity) => intensity === null)) continue

      // Assign symbol based on the maximum match category for this compound
      const matchSymbol = matchMaxMatchCategory === 2 ? 'square' : 'square-open'
      const color = colors[targetId]

      // Get match information for naming
      const {
        target_compound_name,
        target_compound_formula,
        target_ion_formula,
        target_ion_id,
        target_compound_id,
        target_collection_id,
        ionization_mechanism
      } =
        data.find(
          // match correlating with the target
          (match) => match[`target_${level}_id`] === targetId
        ) ?? {}

      // level specific match data
      let name, match_key, all_matches
      switch (level) {
        case 'compound': {
          name = target_compound_name.trim() ? target_compound_name : target_compound_formula
          match_key = `${target_collection_id}_${target_compound_id}`
          all_matches = [...app.data.match.compound.list]
          break
        }
        case 'ion': {
          const compound_prefix = target_compound_name.trim()
            ? target_compound_name
            : target_compound_formula
          name = `${compound_prefix}: ${target_ion_formula}`
          match_key = `${target_collection_id}_${target_compound_id}_${target_ion_id}`
          all_matches = [...app.data.match.ion.list]
          break
        }
      }
      // Add trace for the match
      result.push({
        name,
        x: sampleIds,
        y: intensities,
        mode: 'markers',
        type: 'scatter',
        marker: {
          color,
          size: 10,
          symbol: matchSymbol
        },
        // selection metadata
        matchData: {
          level: level,
          match_key,
          collection_ids: all_matches
            .filter((match) => match[`target_${level}_id`] === targetId)
            .map(({ target_collection_id }) => target_collection_id)
        },
        // tooltip
        customdata: samples.value.map((sample) => sample.datetime),
        text: samples.value.map((sample) => sample.sample_item_name),
        hovertemplate: `
          <i>Match ${level}</i>
          <b># %{x}</b>
          <br>
          <b>${name}</b>
          ${
            level === 'ion' && ionization_mechanism
              ? `<br>Ionization mechanism: ${ionization_mechanism}`
              : ''
          }
          <br>
          <b>%{text}</b>
          <br>
          Peak area sum: %{y:,.0f}
          <br>
          %{customdata}
        `
      })
    }
    // Make trace for TIC
    const ticValues = samples.value.map((sample) => sample.tic) ?? []
    result.push({
      name: 'TIC',
      x: sampleIds,
      y: ticValues,
      customdata: app.data.sample.list?.map((item) => item.datetime) ?? [],
      text: app.data.sample.list?.map((item) => item.sample_item_name) ?? [],
      hovertemplate: `
        <b># %{x}</b>
        <br>
        <b>%{text}</b>
        <br>
        y: %{y:,.0f}
        <br>
        %{customdata}
      `,
      mode: 'markers',
      type: 'scatter',
      marker: {
        color: app.ui.darkmode.active ? '#fff' : '#222',
        size: 10,
        symbol: 'diamond'
      }
    })
    return result
  })

  /**
   * Filter traces by collection
   */
  const traces = computed(
    () =>
      app.ui.filter.collections.length
        ? rawTraces.value.filter(
            ({ matchData }) =>
              matchData // TIC has no match data
                ? matchData.collection_ids.some((collId) =>
                    app.ui.filter.collections
                      .map(({ target_collection_id }) => target_collection_id)
                      .includes(collId)
                  ) // normal data filtered by collection
                : true // TIC is always shown
          )
        : rawTraces.value // show all traces if no filter exists
  )

  return {
    traces
  }
})
