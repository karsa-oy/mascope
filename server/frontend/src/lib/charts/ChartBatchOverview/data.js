import { ref, shallowRef, triggerRef, computed, watch, watchEffect, onUnmounted } from 'vue'
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
   * Per-ion series records from the API, used to construct figure traces.
   * Structure: { target_ion_id, target_compound_name, ionization_mechanism_id, ...,
   *   match_series: { sample_item_ids: [], sample_peak_intensity_sums: [], match_categories: [] } }
   *
   * Held in a shallowRef: the arrays inside are large (one entry per matched
   * sample) and never need deep reactivity — updates assign a new array or
   * call triggerRef explicitly.
   */
  const records = shallowRef([])
  const samples = computed(() => app.data.sample.list ?? [])

  const pending = ref(false)

  /**
   * Fetch per-sample match values for the given ions in columnar form.
   * Scopes samples to the focused batch, unless explicit sample item IDs
   * are given (used when a single sample's matches are (re)created).
   */
  const fetchMatchSeries = async (targetIonIds, sampleItemIds = null) => {
    const scope = sampleItemIds
      ? { sample_item_ids: sampleItemIds }
      : { sample_batch_id: app.data.batch.focusedId }
    const data = await api.http.post(
      `/match/records/ion/series`,
      { ...scope, target_ion_ids: targetIonIds },
      { use: 'read', type: 'load_match_ion_data' }
    )
    // Ions without any match carry no information for the chart
    return data ? data.filter((record) => record.match_series.sample_item_ids.length > 0) : []
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

    if (newlySelectedIds.length > 0) {
      const chunkSize = 100 // How many ions to load per request

      for (let i = 0; i < newlySelectedIds.length; i += chunkSize) {
        const chunk = newlySelectedIds.slice(i, i + chunkSize)
        const newRecords = await fetchMatchSeries(chunk)
        console.debug(
          `🔄 [chart.batch.overview] adding series for ${newRecords.length} of ${chunk.length} ions`
        )
        records.value = records.value.concat(newRecords)
      }
    }
    pending.value = false
  }

  /** Handle ion reload event */
  const handleIonReload = async (event) => {
    console.debug('🔄 [chart.batch.overview] handling match_ion_reload event', event)
    const targetIonId = event.record_id
    // De-select and re-select the ion to trigger data reload
    const selectedIds = app.data.match.ion.selectedIds
    if (selectedIds.includes(targetIonId)) {
      await handleIonsSelected(
        selectedIds.filter((id) => id !== targetIonId),
        selectedIds
      )
      await handleIonsSelected(
        [...selectedIds, targetIonId],
        selectedIds.filter((id) => id !== targetIonId)
      )
    }
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

    const newRecords = await fetchMatchSeries(targetIonIds, [sampleItemId])

    console.debug(
      `🔄 [chart.batch.overview] merging series of ${newRecords.length} ions for new sample ${sampleItemId}`
    )
    // Merge the single-sample values into the existing per-ion series
    const byIonId = new Map(records.value.map((record) => [record.target_ion_id, record]))
    const added = []
    for (const newRecord of newRecords) {
      const existing = byIonId.get(newRecord.target_ion_id)
      if (!existing) {
        added.push(newRecord)
        continue
      }
      const series = existing.match_series
      // Drop any stale entry for this sample before appending (rematch case)
      const staleIndex = series.sample_item_ids.indexOf(sampleItemId)
      if (staleIndex !== -1) {
        series.sample_item_ids.splice(staleIndex, 1)
        series.sample_peak_intensity_sums.splice(staleIndex, 1)
        series.match_categories.splice(staleIndex, 1)
      }
      series.sample_item_ids.push(...newRecord.match_series.sample_item_ids)
      series.sample_peak_intensity_sums.push(...newRecord.match_series.sample_peak_intensity_sums)
      series.match_categories.push(...newRecord.match_series.match_categories)
    }
    records.value = added.length ? records.value.concat(added) : records.value
    triggerRef(records) // in-place series mutations above bypass the shallowRef

    pending.value = false
  }

  /**
   * Handle batch match (re)creation.
   *
   * A batch rematch creates every sample's matches in one burst and emits a
   * single `batch_match_created` event (rather than one `sample_match_created`
   * per sample). Reload all records for the focused batch with the currently
   * selected ions.
   */
  const handleBatchMatchReload = async (event) => {
    console.debug('🔄 [chart.batch.overview] handling batch_match_created event', event)
    // Ignore events for a batch the user is not currently looking at.
    if (
      event?.record?.sample_batch_id &&
      event.record.sample_batch_id !== app.data.batch.focusedId
    ) {
      return
    }
    const targetIonIds = app.data.match.ion.selectedIds
    if (targetIonIds.length === 0) {
      records.value = []
      return
    }

    pending.value = true
    const chunkSize = 100 // How many ions to load per request
    let reloaded = []
    for (let i = 0; i < targetIonIds.length; i += chunkSize) {
      const chunk = targetIonIds.slice(i, i + chunkSize)
      const newRecords = await fetchMatchSeries(chunk)
      reloaded = reloaded.concat(newRecords)
    }
    console.debug(`🔄 [chart.batch.overview] reloaded series for ${reloaded.length} ions`)
    records.value = reloaded
    pending.value = false
  }

  /**
   * Handle sample match removal
   */
  const handleSampleMatchRemoval = (event) => {
    console.debug('🔄 [chart.batch.overview] handling sample_match_deleted event', event)
    const sampleItemId = event.record_id
    // Remove the sample's entry from every ion's series; drop ions left empty
    records.value = records.value.filter((record) => {
      const series = record.match_series
      const index = series.sample_item_ids.indexOf(sampleItemId)
      if (index !== -1) {
        series.sample_item_ids.splice(index, 1)
        series.sample_peak_intensity_sums.splice(index, 1)
        series.match_categories.splice(index, 1)
      }
      return series.sample_item_ids.length > 0
    })
  }

  /**
   * Handle batch match removal
   */
  const handleBatchMatchRemoval = (event) => {
    console.debug('🔄 [chart.batch.overview] handling batch_match_deleted event', event)
    records.value = []
  }

  const resetChart = ref(0) // Reactive trigger for chart reset

  // Watch for batch change - clear records and trigger chart reset
  watch(
    () => app.data.batch.focusedId,
    (batchId, oldBatchId) => {
      if (batchId !== oldBatchId) {
        console.debug(
          '🔄 [chart.batch.overview] batch changed - clearing records and resetting chart'
        )
        records.value = []
        resetChart.value++ // Trigger chart reset
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
  // Socket listeners for match data changes. Keep a reference to each listener
  // so onUnmounted can actually remove it: socket.off only detaches a handler
  // whose identity matches the one passed to socket.on, so an inline arrow
  // registered here could never be removed (leaking a listener per mount).
  const onSampleMatchCreated = (event) => {
    console.debug('📬 [api:sio] sample_match_created received:', event)
    handleNewSample(event)
  }
  const onBatchMatchCreated = (event) => {
    console.debug('📬 [api:sio] batch_match_created received:', event)
    handleBatchMatchReload(event)
  }
  const onSampleMatchDeleted = (event) => {
    console.debug('📬 [api:sio] sample_match_deleted received:', event)
    handleSampleMatchRemoval(event)
  }
  const onBatchMatchDeleted = (event) => {
    console.debug('📬 [api:sio] batch_match_deleted received:', event)
    handleBatchMatchRemoval(event)
  }
  const onMatchIonReload = (event) => {
    console.debug('📬 [api:sio] match_ion_reload received:', event)
    handleIonReload(event)
  }

  api.socket.on('sample_match_created', onSampleMatchCreated)
  api.socket.on('batch_match_created', onBatchMatchCreated)
  api.socket.on('sample_match_deleted', onSampleMatchDeleted)
  api.socket.on('batch_match_deleted', onBatchMatchDeleted)
  api.socket.on('match_ion_reload', onMatchIonReload)

  onUnmounted(() => {
    api.socket.off('sample_match_created', onSampleMatchCreated)
    api.socket.off('batch_match_created', onBatchMatchCreated)
    api.socket.off('sample_match_deleted', onSampleMatchDeleted)
    api.socket.off('batch_match_deleted', onBatchMatchDeleted)
    api.socket.off('match_ion_reload', onMatchIonReload)
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
   * Build traces from per-ion series records (one trace per ion).
   * The per-sample arrays x / customdata / text are identical for every ion
   * trace, so they are built once and shared by reference across traces.
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

    // Shared per-sample arrays and lookups, built once per recompute
    const customdata = samples.value.map((sample) => [sample.datetime, 'counts/s'])
    const text = samples.value.map((sample) => sample.sample_item_name)
    const sampleIndexById = new Map(
      samples.value.map((sample, index) => [sample.sample_item_id, index])
    )
    const colorIndexByIonId = new Map(
      app.data.match.ion.list.map((ion, index) => [ion.target_ion_id, index])
    )

    // Build ion traces (one per ion) only if collection focused (batch overview match records available)
    const ionTraces = filteredRecords.map((record) => {
      const series = record.match_series

      // Y-axis - sample_peak_intensity_sum
      // Build y-values aligned with samples (null where no match)
      const yValues = new Array(samples.value.length).fill(null)
      let maxMatchCategory = 0
      for (let i = 0; i < series.sample_item_ids.length; i++) {
        const sampleIndex = sampleIndexById.get(series.sample_item_ids[i])
        if (sampleIndex === undefined) continue // sample not in current list
        yValues[sampleIndex] = series.sample_peak_intensity_sums[i]
        if (series.match_categories[i] > maxMatchCategory) {
          maxMatchCategory = series.match_categories[i]
        }
      }

      // Build trace name from compound + ion formula
      const compoundName = record.target_compound_name?.trim()
        ? record.target_compound_name
        : record.target_compound_formula
      const traceName = `${compoundName}: ${record.target_ion_formula}`

      const colorIndex = colorIndexByIonId.get(record.target_ion_id) ?? -1

      return {
        name: traceName,
        x: xValues,
        y: yValues,
        mode: 'markers',
        type: 'scattergl',
        marker: {
          color: theme.value[colorIndex % theme.value.length],
          size: 10,
          symbol: maxMatchCategory === 2 ? 'square' : 'square-open'
        },
        // Click metadata for focusing
        matchData: {
          target_ion_id: record.target_ion_id
        },
        // Hover tooltip data (shared across ion traces)
        customdata,
        text,
        hovertemplate: `
          <i>Ion Match</i>
          <b># %{x}</b>
          <br>
          <b>${traceName}</b>
          ${record.ionization_mechanism ? `<br>Mechanism: ${record.ionization_mechanism}` : ''}
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
      customdata: samples.value.map((sample) => [sample.datetime, '']), // [datetime, unit] used in the hovertemplate
      text,
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
      type: 'scattergl',
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
    resetChart,
    pending
  }
})
