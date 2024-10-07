import { ref, computed, watch, onMounted } from 'vue'
import { defineStore } from 'pinia'
import { api } from '@/api/client.js'
import { useApp } from '@/stores'
import { glasbey } from '../colors.js'

export const useChartData = defineStore('chart.batch.overview', () => {
  const app = useApp()
  const traces = ref([])
  const theme = computed(() => (app.ui.darkmode.active ? glasbey.dark : glasbey.light))

  /**
   * Loads compounds of sample_batch from the API filtered by match_category and populates the chart data.
   * @param {String} sample_batch_id - The ID of the selected sample batch.
   */
  const load = async (sample_batch_id, filters) => {
    unload() // Clear traces before loading new data

    let matches, level, queryParams
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
      matches = // API call includes filter for match_category (1 and 2 only)
        (
          await api.client.get(`/match/${level}s`, {
            params: {
              sample_batch_id,
              match_category_min: 1,
              ...queryParams
            }
          })
        )?.data?.data
    } catch (error) {
      throw new Error(`chart.batch.overview - failed to load match ${level}s: ${error}`)
    }
    //  Generate color mapping for target compounds
    let targetIds = [...new Set(matches.map((match) => match[`target_${level}_id`]) ?? [])]
    let colors = Object.fromEntries(
      targetIds.map((targetId, index) => [[targetId], theme.value[index]])
    )

    // X-axis data: sample IDs
    const samples = app.data.sample.list ?? []
    const sampleIds = samples.map((sample) => sample.sample_item_id)

    // Prepare data for hover information
    const customData = samples.map((sample) => sample.datetime)
    const sampleNames = samples.map((sample) => sample.sample_item_name)

    // Loop through filtered target compounds and make traces
    for (let targetId of targetIds) {
      // Y-axis data: intensities (sample_peak_area_sum)
      const intensities = []
      let matchMaxMatchCategory = 1 // Start with minimum match category

      for (let sampleId of sampleIds) {
        let itemMatches = matches.filter((row) => row.sample_item_id === sampleId)
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
      let matchSymbol = matchMaxMatchCategory === 2 ? 'square' : 'square-open'
      let color = colors[targetId]

      // Get match information for naming
      let match = matches.find((match) => match[`target_${level}_id`] === targetId)
      let matchName
      if (level == 'compound') {
        matchName = match.target_compound_name.trim()
          ? match.target_compound_name
          : match.target_compound_formula
      } else if (level == 'ion') {
        matchName = `${
          match.target_compound_name.trim()
            ? match.target_compound_name
            : match.target_compound_formula
        }: ${match.target_ion_formula}`
      }

      // Create the matchData object target IDs
      let match_key
      switch (level) {
        case 'compound':
          match_key = `${match.target_collection_id}_${match.target_compound_id}`
          break
        case 'ion':
          match_key = `${match.target_collection_id}_${match.target_compound_id}_${match.target_ion_id}`
          break
      }
      const matchData = {
        level,
        match_key
      }

      const hovertemplate = `
        <i>Match ${level}</i>
        <b># %{x}</b>
        <br>
        <b>${matchName}</b>
        ${
          level === 'ion' && match.ionization_mechanism
            ? `<br>
        Ionization mechanism: ${match.ionization_mechanism}`
            : ''
        }
        <br>
        <b>%{text}</b>
        <br>
        Peak area sum: %{y:,.0f}
        <br>
        %{customdata}
      `
      // Add trace for the match
      traces.value.push({
        name: matchName,
        x: sampleIds,
        y: intensities,
        matchData, // Include matchData
        customdata: customData,
        text: sampleNames,
        hovertemplate,
        mode: 'markers',
        type: 'scatter',
        marker: {
          color,
          size: 10,
          symbol: matchSymbol
        }
      })
    }
    // Make trace for TIC
    const ticValues = samples.map((sample) => sample.tic) ?? []
    traces.value.push({
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
  }

  /**
   * Clears the chart data by resetting the `traces` array.
   * This function is called to unload the chart when:
   * - No batch is selected.
   * - There are no samples.
   * - The samples do not belong to the currently selected batch.
   */
  const unload = () => {
    traces.value = []
  }

  /**
   * Watches for changes in both batch selection and loaded samples to update the chart data.
   * - If no batch is selected or the sample list is empty, it unloads the chart data.
   * - Checks that all samples belong to the currently selected batch.
   *   - If not, it unloads the chart data.
   * - When samples are ready and belong to the current batch, it calls `load` to reload the chart data.
   *
   * The watcher is configured with:
   * - `immediate: true` to run immediately upon setup.
   * - `deep: true` to react to changes within the `sampleList` array.
   *
   * @watch
   * @param {[number|null, Array]} newValues - The new values of the watched sources.
   *   - `newValues[0]` (`batchId`): The currently selected batch ID.
   *   - `newValues[1]` (`sampleList`): The current list of loaded samples.
   */
  watch(
    [
      () => app.data.batch.focused?.sample_batch_id, // focused batch
      () => app.data.sample.list, // loaded samples
      () => app.ui.filter.mechanism // filtered mechanism
    ],
    async ([batchId, sampleList, mechanismFilter]) => {
      // requirements
      const batchFocused = batchId
      const samplesExist = sampleList?.length
      const samplesReady = sampleList?.every((sample) => sample.sample_batch_id === batchId)
      // either load or unload, based on requirements
      if (!batchFocused || !samplesExist || !samplesReady) {
        // unload chart if any dependency is unmet
        unload()
        return
      } else {
        const filters = mechanismFilter ? { mechanism: mechanismFilter } : null
        // load the chart if all requirements are met
        await load(batchId, filters)
      }
    },
    { immediate: true, deep: true }
  )

  // Listen for `sample_batch_reload` event and reload data
  onMounted(() => {
    api.socket.on('sample_batch_reload', async () => {
      const batchId = app.data.batch.focused?.sample_batch_id
      if (batchId) {
        await load(batchId)
      }
    })
  })

  return {
    traces
  }
})
