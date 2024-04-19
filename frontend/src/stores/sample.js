import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

import { api } from '@/api'

import { useAppStore } from './app'
import { useBatchStore } from './batch'
import { useCalibrationStore } from './calibration'
import { useTargetsStore } from './targets'

export const useSampleStore = defineStore('sample', () => {
  const active = ref(null)
  // matches
  const matched = ref(null)
  const matchCollections = ref(null)
  const matchCompounds = ref(null)
  const matchIons = ref(null)
  const matchIsotopes = ref(null)

  // getters

  const sampleTypes = computed(() => [
    'FILTER_REGENERATION',
    'FILTER_BACKGROUND',
    'INSTRUMENT_BACKGROUND',
    'BLANK',
    'SAMPLE',
    'UNKNOWN',
    'ONLINE' // At the moment not selectable from the UI
  ])
  const getMatchCollections = computed(() => matchCollections.value ?? [])
  const maxMatchCategory = computed(() => (compounds = null) => {
    if (compounds === null) compounds = matchCompounds.value
    return compounds && compounds.length > 0
      ? Math.max(...compounds.map((compound) => compound.match_category))
      : null
  })

  // actions

  // data loading
  async function load(sample) {
    // reset if previous sample loaded
    if (active.value) await unload()
    const sampleItemId = sample.sample_item_id
    api.emit('subscribe', sampleItemId)
    active.value = sample
    await loadSampleData(sampleItemId)
    const calibrationStore = useCalibrationStore()
    await calibrationStore.load(sample)
  }

  async function loadSampleData(sampleItemId) {
    // Check if matches exist for the given sampleItemId
    const sampleMatches = await getSampleMatches(sampleItemId)
    matched.value = sampleMatches.length > 0 ? 1 : 0

    // Get detailed sample data
    const sampleData = await getSampleData(sampleItemId)

    // Set the selection of the active collection
    const targetStore = useTargetsStore()
    const activeCollection = targetStore.activeCollection
    matchCollections.value = sampleData.match_collections?.map((coll) => {
      if (activeCollection && activeCollection.target_collection_id === coll.target_collection_id) {
        coll.selection = 2
      } else {
        coll.selection = 0
      }
      return coll
    })
    matchCompounds.value = sampleData.match_compounds
    matchIons.value = sampleData.match_ions
    matchIsotopes.value = sampleData.match_isotopes
  }

  async function unload() {
    if (!active.value) return
    api.emit('unsubscribe', active.value.sample_item_id)

    active.value = null

    matched.value = null
    matchCollections.value = null
    matchCompounds.value = null
    matchIons.value = null
    matchIsotopes.value = null

    const calibrationStore = useCalibrationStore()
    calibrationStore.unload(null) // should this be awaited?
  }

  async function reload(sample = null) {
    const sampleToLoad = sample ?? active.value
    if (sampleToLoad) {
      await unload()
      await load(sampleToLoad)
    }
  }

  // http client endpoints
  async function getSampleData(sampleId) {
    const targetStore = useTargetsStore()
    const alarmsList = targetStore.alarmsList

    const body = {
      alarms_list: alarmsList
    }

    const sampleData = await api.request({
      httpMethod: 'getSample',
      requestData: {
        sampleId,
        body
      },
      errorMessage: `Failed to load the sample data.`
    })
    return sampleData.data
  }

  async function getSampleMatches(sampleItemId) {
    const sampleMatches = await api.request({
      httpMethod: 'getAllMatches',
      requestData: {
        sample_item_id: sampleItemId
      },
      errorMessage: `Failed to check for matches of the sample.`
    })
    return sampleMatches.data
  }

  async function create(sample) {
    await api.http.createSampleItem(sample)
  }
  async function update(sample) {
    await api.http.updateSampleItem(sample.sample_item_id, sample)
  }
  async function deleteSampleItem(sampleItemId) {
    await api.http.deleteSampleItem(sampleItemId)
  }
  async function matchSampleCompute(sample) {
    const sampleId = sample.sample_item_id
    await api.http.matchSampleCompute({ sampleId })
  }
  async function matchSampleRematch(sample) {
    const sampleId = sample.sample_item_id
    await api.http.matchSampleRematch({ sampleId })
  }

  async function copySample(sample) {
    const sampleId = sample.sample_item_id
    const body = {
      sample_batch_id: sample.sample_batch_id,
      sample_item_name: sample.sample_item_name
    }
    return await api.process({
      httpMethod: 'copySampleItem',
      requestData: { sampleId, body },
      progressNotificationPayload: {
        action: 'copy',
        type: 'sample',
        message: `Copying sample "${body.sample_item_name}" to "${body.workspace_name}/${body.sample_batch_name}", please wait`
      }
    })
  }

  // Attribute templates
  async function createAttributeTemplate(newTemplate) {
    return await api.process({
      httpMethod: 'createAttributeTemplate',
      requestData: newTemplate,
      successMessage: `Attribute template "${newTemplate.name}" created successfully!`,
      errorMessage: `Failed to create attribute template "${newTemplate.name}". Please try again.`
    })
  }

  async function updateAttributeTemplate(template) {
    const templateId = template.attribute_template_id
    const body = template
    return await api.process({
      httpMethod: 'updateAttributeTemplate',
      requestData: { templateId, body },
      successMessage: `Attribute template "${template.name}" updated successfully!`,
      errorMessage: `Failed to update attribute template "${template.name}". Please try again.`
    })
  }

  async function deleteAttributeTemplate(template) {
    const templateId = template.attribute_template_id
    const templateName = template.name
    return await api.process({
      httpMethod: 'deleteAttributeTemplate',
      requestData: { templateId, templateName },
      successNotificationType: 'deleted',
      successMessage: `Attribute template "${templateName}" was deleted successfully!`,
      errorMessage: `Failed to delete attribute template ${templateName}. Please try again.`
    })
  }

  // backend notifications
  async function onSampleBatchExportPeaksFailed(error) {
    const appStore = useAppStore()
    await appStore.pushNotify({
      message: error,
      key: Math.random()
    })
  }
  async function onSampleBatchExportPeaksReady() {
    const appStore = useAppStore()
    await appStore.pushNotify({
      message: 'Sample batch peak export finished',
      key: Math.random()
    })
  }
  async function onSampleItemCreated(sample_item_id) {
    const batchStore = useBatchStore()
    await batchStore.reload(null)
    const sampleItem = batchStore.sampleItem(sample_item_id)
    await load(sampleItem)
  }
  async function onSampleProcessingFinished() {
    console.log(`sample item processing was finished`)
    // TODO can be used for the Scenthound Page and for 'Process File' buttnon on the Home page for processing 1 selected sample_file
  }

  // selection
  async function updateCollectionSelection({ collectionId, selectionValue }) {
    // Only one collection can be selected at a time
    matchCollections.value
      .filter((coll) => coll.target_collection_id !== collectionId && coll.selection === 2)
      .forEach((coll) => (coll.selection = 0))

    const collection = matchCollections.value.find(
      (coll) => coll.target_collection_id === collectionId
    )
    if (collection) {
      collection.selection = selectionValue
    }
  }

  return {
    // state
    active,
    matched,
    matchCollections,
    matchCompounds,
    matchIons,
    matchIsotopes,
    // getters
    sampleTypes,
    getMatchCollections,
    maxMatchCategory,
    // actions,
    load,
    loadSampleData,
    unload,
    reload,
    getSampleData,
    getSampleMatches,
    create,
    update,
    deleteSampleItem,
    matchSampleCompute,
    matchSampleRematch,
    copySample,
    createAttributeTemplate,
    updateAttributeTemplate,
    deleteAttributeTemplate,
    onSampleBatchExportPeaksFailed,
    onSampleBatchExportPeaksReady,
    onSampleItemCreated,
    onSampleProcessingFinished,
    updateCollectionSelection
  }
})
