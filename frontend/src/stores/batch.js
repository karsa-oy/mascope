import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

import { api } from '@/api'

import { useTargetsStore } from './targets.js'
import { useSampleStore } from './sample.js'
import { useWorkspaceStore } from './workspace.js'
import { useAppStore } from './app.js'
import { useMzFit } from './mzFit.js'

export const useBatchStore = defineStore('batch', () => {
  const active = ref(null)
  // samples
  const sampleItems = ref([])
  // targets
  const targetCollections = ref([])
  const targetCompounds = ref([])
  const targetIons = ref([])
  const targetIsotopes = ref([])

  // matches
  const matchSamples = ref([]) // TODO_loading not used
  const matchCompounds = ref([])
  const matchIons = ref([])
  // build parameters
  const paramCalibrationCollection = ref([])
  const paramIonMechanisms = ref([])

  const loading = ref(false)

  // getters

  // get row from id
  const sampleItem = computed(
    () => (sampleItemId) =>
      sampleItems.value.find((row) => row.sample_item_id == sampleItemId) ?? null
  )

  // data loading
  async function load(batchId) {
    loading.value = true
    if (active.value) await unload()
    api.emit('subscribe', batchId)
    await loadBatch(batchId)
    await loadBatchSamplesData(batchId)
    loading.value = false
    await unpackParams()
    await loadBatchTargets(batchId)
  }

  async function loadBatch(batchId) {
    const batch = await getBatch(batchId)
    if (!batch) return
    active.value = batch
  }

  async function loadBatchSamplesData(batchId) {
    const batchData = await getBatchSamplesData(batchId)
    if (!batchData) return
    batchData.data.forEach((row, i) => (row.index = (i + 1).toString()))
    sampleItems.value = batchData.data
    if (!batchData.batch_matches_info) return
    matchSamples.value = batchData.batch_matches_info?.match_samples
    matchCompounds.value = batchData.batch_matches_info?.match_compounds
    matchIons.value = batchData.batch_matches_info?.match_ions
  }

  async function loadBatchTargets(batchId) {
    const targetsStore = useTargetsStore()
    const alarms_list = targetsStore.alarmsList
    const batchTargets = (
      await api.request.read({
        method: 'getBatchTargets',
        body: {
          batchId,
          body: {
            alarms_list
          }
        }
      })
    )?.data
    if (!batchTargets) return
    let newTargetCollections = batchTargets.target_collections

    const targetStore = useTargetsStore()
    const activeCollection = targetStore.activeCollection
    if (newTargetCollections) {
      newTargetCollections = newTargetCollections.map((coll) => {
        if (
          activeCollection &&
          activeCollection.target_collection_id === coll.target_collection_id
        ) {
          coll.selection = 2
        } else {
          coll.selection = 0
        }
        return coll
      })
    }
    targetCollections.value = newTargetCollections
    targetCompounds.value = batchTargets.target_compounds
    targetIons.value = batchTargets.target_ions
    targetIsotopes.value = batchTargets.target_isotopes
  }

  async function reload(batch = null) {
    const appStore = useAppStore()
    const wasMeasuring = appStore.mode.measuring

    const targetStore = useTargetsStore()
    const batchToLoad = batch ?? active.value
    if (!batchToLoad) return

    await unload(false)
    const batchToLoadId = batchToLoad.sample_batch_id
    await load(batchToLoadId)

    if (wasMeasuring) {
      appStore.mode.measuring = true
    }

    const sampleStore = useSampleStore()
    const activeSampleId = sampleStore.active?.sample_item_id ?? null
    if (activeSampleId) {
      const sample = sampleItem.value(activeSampleId)
      sample.selection = 3
      await sampleStore.reload(sample)
    }
    const activeCollection = targetStore.activeCollection
    if (activeCollection) {
      const activeCollectionId = activeCollection.target_collection_id
      const matchingCollection = targetCollections.value?.find(
        (coll) => coll.target_collection_id === activeCollectionId
      )
      if (matchingCollection) {
        // set collection selection
        const collection = targetCollections.value?.find(
          (coll) => coll.target_collection_id === activeCollectionId
        )
        if (collection) collection.selection = 2
      } else {
        // Dispatch to targets module to update selection there as well
        targetStore.updateCollectionSelection({
          collectionId: activeCollectionId,
          selectionValue: 0
        })
      }
    }
  }
  async function unload(propagate = true) {
    if (!active.value) return
    api.emit('unsubscribe', active.value.sample_batch_id)
    active.value = null
    // parameters
    resetParams()
    // samples
    sampleItems.value = []
    // targets
    targetCollections.value = []
    targetCompounds.value = []
    targetIons.value = []
    targetIsotopes.value = []
    // matches
    matchSamples.value = []
    matchCompounds.value = []
    matchIons.value = []
    const sampleStore = useSampleStore()
    if (propagate) sampleStore.unload(null)
  }

  // parameters
  async function resetParams() {
    // reset parameters to default values
    paramCalibrationCollection.value = []
    paramIonMechanisms.value = []
  }
  async function unpackParams() {
    // unpack parameters from batch object into state variables
    const buildParams = active.value?.build_params ?? null
    if (!buildParams) return
    for (const param in buildParams) {
      if (param.toUpperCase().startsWith('CALIBRATION')) {
        paramCalibrationCollection.value = buildParams[param]
      }
      if (param.toUpperCase().startsWith('ION')) {
        paramIonMechanisms.value = buildParams[param]
      }
    }
  }

  // http client endpoints
  async function getBatch(batchId) {
    return await api.request.read({
      method: 'getBatch',
      body: { batchId }
    })
  }

  async function getBatchSamplesData(batchId) {
    const targetStore = useTargetsStore()
    const alarmsList = targetStore.alarmsList

    const body = {
      sample_batch_id: batchId,
      batch_matches_info: true,
      sort: 'datetime_utc',
      alarms_list: alarmsList
    }

    return await api.request.read({
      method: 'getAllSamples',
      body: body
    })
  }

  async function importItems({ batch, sample_items }) {
    const mzFit = useMzFit()
    return await api.request.process({
      method: 'importSamplesToBatch',
      body: {
        batch,
        body: {
          sample_items,
          params: mzFit.params
        }
      }
    })
  }
  async function createBatch(newBatch) {
    return await api.request.create({
      method: 'createBatch',
      body: newBatch
    })
  }
  async function updateBatch(newBatch) {
    const batchId = newBatch.sample_batch_id
    const body = newBatch
    return await api.request.update({
      method: 'updateBatch',
      body: { batchId, body }
    })
  }

  async function deleteBatch(batch) {
    return await api.request.process({
      method: 'deleteBatch',
      body: batch
    })
  }
  async function copyBatch(batchCopyData) {
    const batchId = batchCopyData.sample_batch_id
    const body = {
      workspace_id: batchCopyData.workspace_id,
      sample_batch_name: batchCopyData.sample_batch_name,
      sample_batch_description: batchCopyData.sample_batch_description
    }
    return await api.request.process({
      method: 'copySampleBatch',
      body: { batchId, body }
    })
  }

  async function exportPeaks(sampleBatch) {
    return await api.request.process({
      method: 'batchExportPeakData',
      body: sampleBatch
    })
  }

  async function rematchBatch(batch = null) {
    const batchId = batch?.sample_batch_id ?? active.value.sample_batch_id
    if (!batchId) return
    return await api.request.process({
      method: 'rematchBatch',
      body: { batchId }
    })
  }

  // backend notifications
  async function onSampleBatchReload() {
    await reload()
  }

  // selection
  async function batchToggle(batch) {
    const workspaceStore = useWorkspaceStore()
    //workspaceStore.batches.forEach((row) => (row.selection = 0))
    if (!batch || active.value?.sample_batch_id == batch?.sample_batch_id) {
      unload()
    } else {
      load(batch.sample_batch_id)
      workspaceStore.batches
        .filter((row) => row.sample_batch_id == batch.sample_batch_id)
        .forEach((row) => (row.selection = 2))
    }
  }

  return {
    // state
    active,
    loading,
    sampleItems,
    targetCollections,
    targetCompounds,
    targetIons,
    targetIsotopes,
    matchSamples,
    matchCompounds,
    matchIons,
    paramCalibrationCollection,
    paramIonMechanisms,
    // getters
    sampleItem,
    // actions
    load,
    reload,
    unload,
    importItems,
    createBatch,
    updateBatch,
    deleteBatch,
    copyBatch,
    exportPeaks,
    rematchBatch,
    onSampleBatchReload,
    batchToggle
  }
})
