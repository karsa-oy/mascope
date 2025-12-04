import { ref, computed, watch, watchEffect } from 'vue'
import { defineStore } from 'pinia'
import { api } from '@/api'
import { beautifySnakeCase } from '@/lib/utils'
import { useApp } from '@/stores'
import { glasbey } from '../colors.js'

export const useChartData = defineStore('chart.batch.overview', () => {
  const app = useApp()
  const theme = computed(() => (app.ui.darkmode.active ? glasbey.dark : glasbey.light))

  app.ui.chart.register({
    name: 'ChartBatchOverview',
    clear: () => {
      console.debug('📊 [ChartBatchOverview]: skip clear')
    }
  })

  /**
   * Flat records from batch_overview store - already filtered (match_category > 0) and joined
   * Structure: { sample_item_id, target_ion_id, sample_peak_intensity_sum, target_compound_name, ... }
   */
  const records = ref([])
  const samples = computed(() => app.data.sample.list ?? [])

  const pending = ref(false)

  /**
   * Parse API response data into chart records format
   */
  const parseMatchRecords = (data) => {
    return data.map((record) => ({
      // Identifiers (for mapping/focusing/filtering)
      target_ion_id: record.target_ion_id,
      sample_item_id: record.match.sample_item_id,
      match_ion_id: record.match.match_ion_id,
      ionization_mechanism_id: record.ionization_mechanism_id,
      // Display data (for trace building)
      target_ion_formula: record.target_ion_formula,
      target_compound_name: record.target_compound_name,
      target_compound_formula: record.target_compound_formula,
      ionization_mechanism: record.ionization_mechanism,
      // Chart data (for plotting)
      sample_peak_intensity_sum: record.match.sample_peak_intensity_sum || null,
      match_category: record.match.match_category,
      // unused in chart, but useful for debugging
      match_score: record.match.match_score || null
    }))
  }

  /**
   * Fetch match records for given sample and ion IDs
   */
  const fetchMatchRecords = async (sampleItemIds, targetIonIds) => {
    const data = await api.http.post(
      `/match/records/ion`,
      { sample_item_ids: sampleItemIds, target_ion_ids: targetIonIds },
      { use: 'read', type: 'load_match_ion_data' }
    )
    return data ? parseMatchRecords(data) : []
  }

  /**
   * Handle ion selection changes
   */
  async function handleIonsSelected(nextSelected, prevSelected) {
    // Remove records for unselected ions
    console.debug(`🔄 [chart.batch.overview] removing datapoints for unselected ion(s)`)
    records.value = records.value.filter((record) => nextSelected.includes(record.target_ion_id))

    pending.value = true

    // Process newly selected ions
    const newlySelectedIds = nextSelected.filter((id) => !prevSelected.includes(id))

    for (const ionId of newlySelectedIds) {
      const sampleItemIds = app.data.sample.list.map((s) => s.sample_item_id)
      const newRecords = await fetchMatchRecords(sampleItemIds, [ionId])

      console.debug(
        `🔄 [chart.batch.overview] adding ${newRecords.length} datapoints for newly selected ion ${ionId}`
      )
      records.value = [...records.value, ...newRecords]
    }

    pending.value = false
  }

  /**
   * Handle new sample match creation
   */
  const handleNewSample = async (event) => {
    console.debug('🔄 [chart.batch.overview] handling sample_match_created event', event)
    const sampleItemId = event.record.sample_item_id
    const targetIonIds = app.data.match.ion.selectedIds

    if (targetIonIds.length === 0) return // no selected ions, nothing to do

    pending.value = true

    const newRecords = await fetchMatchRecords([sampleItemId], targetIonIds)

    console.debug(
      `🔄 [chart.batch.overview] adding ${newRecords.length} datapoints for new sample ${sampleItemId}`
    )
    records.value = [...records.value, ...newRecords]

    pending.value = false
  }

  /**
   * Handle sample match removal
   */
  const handleSampleMatchRemoval = (event) => {
    console.debug('🔄 [chart.batch.overview] handling sample_match_deleted event', event)
    const sampleItemId = event.record_id
    records.value = records.value.filter((record) => record.sample_item_id !== sampleItemId)
  }

  /**
   * Handle batch match removal
   */
  const handleBatchMatchRemoval = (event) => {
    console.debug('🔄 [chart.batch.overview] handling batch_match_deleted event', event)
    records.value = []
  }


  // Watch for batch change - clear records and trigger chart reset
  watch(
    () => app.data.batch.focusedId,
    (batchId, oldBatchId) => {
      if (batchId !== oldBatchId) {
        console.debug(
          '🔄 [chart.batch.overview] batch changed - clearing records and resetting chart'
        )
        records.value = []
      }
    }
  )

  // Watch for ion selection changes
  watch(
    () => app.data.match.ion.selectedIds,
    async (nextSelected, prevSelected) => {
      await handleIonsSelected(nextSelected, prevSelected)
    }
  )
  // Socket listeners for match data changes
  api.socket.on('sample_match_created', (event) => {
    console.debug('📬 [api:sio] sample_match_created received:', event)
    handleNewSample(event)
  })
  api.socket.on('sample_match_deleted', (event) => {
    console.debug('📬 [api:sio] sample_match_deleted received:', event)
    handleSampleMatchRemoval(event)
  })
  api.socket.on('batch_match_deleted', (event) => {
    console.debug('📬 [api:sio] batch_match_deleted received:', event)
    handleBatchMatchRemoval(event)
  })
  /**
   * X-axis field selection
   */
  const inferType = (field) => {
    const withField = samples.value.filter((item) => field in item)
    const types = [
      ...new Set(withField.map((item) => (item[field] ? typeof item[field] : 'null')))
    ].filter((type) => type !== 'null')
    return types.length === 1 ? types[0] : 'unknown'
  }

  const xFields = computed(() => {
    const standard = [
      ...new Set(
        samples.value
          ?.map((item) => Object.keys(item ?? {}))
          .flat()
          .filter((field) => field !== 'sample_item_attributes')
      )
    ].map((field) => ({ field, kind: 'standard' }))

    const custom = [
      ...new Set(
        samples.value?.map((item) => Object.keys(item?.sample_item_attributes ?? {})).flat()
      )
    ].map((field) => ({ field, kind: 'custom' }))

    return [...standard, { field: 'time_of_day', kind: 'custom' }, ...custom]
      .map(({ field, kind }) => ({
        field,
        kind,
        label: beautifySnakeCase(field),
        type: kind === 'custom' ? 'string' : inferType(field)
      }))
      .filter(({ type }) => type !== 'object')
  })

  const xField = ref()

  watchEffect(() => {
    xField.value = xFields.value.find(({ field }) => field === 'datetime')
  })

  /**
   * Build traces from flat record structure
   * Records are already filtered (match_category > 0) and contain all needed data
   */
  const traces = computed(() => {
    // Guard: no samples = no chart
    if (!samples.value.length) return []

    // Filter records by ionization mechanism (if filter active)
    const filteredRecords = records.value.filter((record) =>
      app.data.ionization.mechanism.filteredIds.includes(record.ionization_mechanism_id)
    )

    const xFieldName = xField.value?.field || 'index'

    // Generate x-values based on selected xField
    const xValues = samples.value.map(
      xFieldName === 'time_of_day'
        ? (sample) => `1970-01-01T${sample.datetime.split('T')[1].split('.')[0]}`
        : (sample) => sample[xFieldName]
    )

    // Build ion traces (one per ion) only if collection focused (batch overview match records available)
    const ionTraces = !filteredRecords.length
      ? []
      : Object.entries(
          // Group records by target_ion_id for trace building
          filteredRecords.reduce((groups, record) => {
            const ionId = record.target_ion_id
            if (!groups[ionId]) groups[ionId] = []
            groups[ionId].push(record)
            return groups
          }, {})
        ).map(([ionId, ionRecords], index) => {
          // Create sample_item_id → intensity mapping for this ion
          const intensityMap = ionRecords.reduce((map, record) => {
            map[record.sample_item_id] = record.sample_peak_intensity_sum
            return map
          }, {})

          // Y-axis - sample_peak_intensity_sum
          // Build y-values aligned with samples (null where no match)
          const yValues = samples.value.map((sample) => intensityMap[sample.sample_item_id] ?? null)

          // Get representative record for metadata (all records for same ion have same metadata)
          const rep = ionRecords[0]
          const maxMatchCategory = Math.max(...ionRecords.map((r) => r.match_category))

          // Build trace name from compound + ion formula
          const compoundName = rep.target_compound_name?.trim()
            ? rep.target_compound_name
            : rep.target_compound_formula
          const traceName = `${compoundName}: ${rep.target_ion_formula}`

          return {
            name: traceName,
            x: xValues,
            y: yValues,
            mode: 'markers',
            type: 'scatter',
            marker: {
              color: theme.value[index % theme.value.length],
              size: 10,
              symbol: maxMatchCategory === 2 ? 'square' : 'square-open'
            },
            // Click metadata for focusing
            matchData: {
              target_ion_id: rep.target_ion_id,
              match_ion_id: rep.match_ion_id
            },
            // Hover tooltip data
            customdata: samples.value.map((sample) => [sample.datetime, 'counts/s']),
            text: samples.value.map((sample) => sample.sample_item_name),
            hovertemplate: `
              <i>Ion Match</i>
              <b># %{x}</b>
              <br>
              <b>${traceName}</b>
              ${rep.ionization_mechanism ? `<br>Mechanism: ${rep.ionization_mechanism}` : ''}
              <br>
              <b>%{text}</b>
              <br>
              Intensity: %{y:,.2e} %{customdata[1]}
              <br>
              %{customdata[0]}
              <extra></extra>
            ` // use "<extra></extra>" to get rid of extra block from the hoverbox
          }
        })

    // Always add TIC trace
    ionTraces.push({
      // Make trace for TIC
      name: 'TIC',
      x: xValues,
      y: samples.value.map((sample) => sample.tic),
      customdata: [...Array(samples.value.length).keys()].map((i) => [
        samples.value[i].datetime,
        ''
      ]), // Add [datetime, unit] in customdata field to use in the hovertemplate
      text: samples.value.map((sample) => sample.sample_item_name),
      hovertemplate: `
        <b># %{x}</b>
        <br>
        <b>%{text}</b>
        <br>
        TIC: %{y:,.2e}
        <br>
        %{customdata[0]}
        <extra></extra>
      `, // use "<extra></extra>" to get rid of extra block from the hoverbox
      mode: 'markers',
      type: 'scatter',
      marker: {
        color: app.ui.darkmode.active ? '#888' : '#222',
        size: 10,
        symbol: 'diamond-open'
      }
    })
    return ionTraces
  })

  return {
    samples,
    traces,
    xFields,
    xField,
    pending
  }
})
