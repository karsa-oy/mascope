import { ref, computed, watch, onMounted } from 'vue'
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

  /**
   * Loads compounds of sample_batch from the API filtered by match_category and populates the chart data.
   * @param {String} sample_batch_id - The ID of the selected sample batch.
   */
  const load = async (sample_batch_id) => {
    unload() // Clear traces before loading new data

    let compounds
    try {
      compounds = // API call includes filter for match_category (1 and 2 only)
        (
          await api.client.get(`/match/compounds`, {
            params: {
              sample_batch_id,
              show_target_compound: true,
              match_category: 1
            }
          })
        )?.data?.data
    } catch (error) {
      throw new Error(`chart.batch.overview - failed to load match compounds: ${error}`)
    }

    //  Generate color mapping for target compounds
    let compoundIds = [...new Set(compounds.map((compound) => compound.target_compound_id) ?? [])]
    let colors = Object.fromEntries(
      compoundIds.map((compoundId, index) => [[compoundId], theme.value[index]])
    )

    // X-axis data: sample IDs
    const samples = app.data.sample.list ?? []
    const sampleIds = samples.map((sample) => sample.sample_item_id)

    // Prepare data for hover information
    const customData = samples.map((sample) => sample.datetime)
    const sampleNames = samples.map((sample) => sample.sample_item_name)

    // Loop through filtered target compounds and make traces
    for (let compoundId of compoundIds) {
      // Y-axis data: intensities (sample_peak_area_sum)
      const intensities = []
      let compoundMaxMatchCategory = 1 // Start with minimum match category

      for (let sampleId of sampleIds) {
        let itemMatches = compounds.filter((row) => row.sample_item_id === sampleId)
        let sampleCompoundStats = itemMatches
          .filter((match) => match.target_compound_id === compoundId)
          .map((compoundMatch) => ({
            match_category: compoundMatch.match_category,
            intensity: compoundMatch.sample_peak_area_sum
          }))[0]

        if (sampleCompoundStats) {
          intensities.push(
            sampleCompoundStats.match_category > 0 ? sampleCompoundStats.intensity : null
          )
          // Update the maximum match category for this compound
          if (sampleCompoundStats.match_category > compoundMaxMatchCategory) {
            compoundMaxMatchCategory = sampleCompoundStats.match_category
          }
        } else {
          intensities.push(null)
        }
      }

      // Skip if no valid intensity data
      if (intensities.every((intensity) => intensity === null)) continue

      // Assign symbol based on the maximum match category for this compound
      let compoundSymbol = compoundMaxMatchCategory === 2 ? 'square' : 'square-open'
      let color = colors[compoundId]

      // Get compound information for naming
      let compound = compounds.find((target) => target.target_compound_id === compoundId)
      let compoundName = compound.target_compound_name.trim()
        ? compound.target_compound_name
        : compound.target_compound_formula

      // Add trace for the compound
      traces.value.push({
        name: compoundName,
        target_compound_id: compoundId,
        x: sampleIds,
        y: intensities,
        customdata: customData,
        text: sampleNames,
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
    const ticValues = samples.map((sample) => sample.tic) ?? []
    traces.value.push({
      name: 'TIC',
      x: sampleIds,
      y: ticValues,
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
    [() => app.data.batch.focused?.sample_batch_id, () => app.data.sample.list],
    async ([batchId, sampleList]) => {
      // If no batch is selected, unload the chart data
      if (!batchId) {
        unload()
        return
      }

      // If no samples, unload the chart data
      if (!sampleList?.length) {
        unload()
        return
      }

      // Check that samples belong to the currently selected batch
      const samplesReady = sampleList.every((sample) => sample.sample_batch_id === batchId)
      if (!samplesReady) {
        unload()
        return
      }

      // Reload the chart if batchId changes or the samples are ready and different
      await load(batchId)
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
