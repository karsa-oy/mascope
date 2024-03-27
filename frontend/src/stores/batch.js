import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

import { api } from '@/api'

import { useTargetsStore } from './targets.js'
import { useSampleStore } from './sample.js'
import { useNotificationStore } from './notification.js'
import { useWorkspaceStore } from './workspace.js'

export const useBatchStore = defineStore('batch', () => {
  const active = ref(null)
  // samples
  const sampleItems = ref(null)
  // targets
  const targetCollections = ref(null)
  const targetCompounds = ref(null)
  const targetIons = ref(null)
  const targetIsotopes = ref(null)

  // matches
  const matchSamples = ref(null) // TODO_loading not used
  const matchCompounds = ref(null)
  const matchIons = ref(null)
  // build parameters
  const paramCalibrationCollection = ref([])
  const paramIonMechanisms = ref([])

  // getters

  // get all rows as proxy array
  const getSampleItems = computed(() => sampleItems.value ?? [])
  const getTargetCollections = computed(() => targetCollections.value ?? [])
  const getTargetCompounds = computed(() => targetCompounds.value ?? [])
  const getTargetIons = computed(() => targetIons.value ?? [])
  const getTargetIsotopes = computed(() => targetIsotope.value ?? [])

  // get row from id
  const sampleItem = computed(() => {
    const sampleItems = getSampleItems.value
    return (sampleItemId) => sampleItems.find((row) => row.sample_item_id == sampleItemId) ?? null
  })
  const targetCollection = computed(() => {
    const targetCollections = getTargetCollections.value
    return (targetCollectionId) =>
      targetCollections.find((row) => row.target_collection_id == targetCollectionId) ?? null
  })
  const targetCompound = computed(() => {
    const targetCompounds = getTargetCompounds.value
    return (targetCompoundId) =>
      targetCompounds.find((row) => row.target_compound_id == targetCompoundId) ?? null
  })
  const targetIon = computed(() => {
    const targetIons = getTargetIons.value
    return (targetIonId) => targetIons.find((row) => row.target_ion_id == targetIonId) ?? null
  })
  const targetIsotope = computed(() => {
    const targetIsotopes = getTargetIsotopes.value
    return (targetIsotopeId) =>
      targetIsotopes.find((row) => row.target_isotope_id == targetIsotopeId) ?? null
  })
  // get selected
  const sampleItemsSelected = computed(() =>
    getSampleItems.value.filter((sampleItem) => sampleItem.selection >= 2)
  )
  const sampleItemFocused = computed(
    () => getSampleItems.value.find((sampleItem) => sampleItem.selection == 3) ?? null
  )
  const targetCollectionsSelected = computed(() =>
    getTargetCollections.value.filter((row) => row.selection >= 2)
  )
  const targetCompoundsSelected = computed(() =>
    getTargetCompounds.value.filter((row) => row.selection >= 2)
  )
  const targetIonsSelected = computed(() => getTargetIons.value.filter((row) => row.selection >= 2))
  const targetIsotopesSelected = computed(() =>
    getTargetIsotopes.value.filter((row) => row.selection >= 2)
  )

  // actions

  function setCollectionSelection({ collectionId, selectionValue }) {
    const collection = targetCollections.value?.find(
      (coll) => coll.target_collection_id === collectionId
    )
    if (collection) collection.selection = selectionValue
  }

  // data loading
  async function load(batchId) {
    if (active.value) await unload()
    api.emit('subscribe', batchId)
    await loadBatch(batchId)
    await loadBatchSamplesData(batchId)
    await unpackParams()
    await loadBatchTargets(batchId)
  }

  async function loadBatch(batchId) {
    const batch = await getBatch(batchId)
    active.value = batch
  }

  async function loadBatchSamplesData(batchId) {
    const batchData = await getBatchSamplesData(batchId)

    batchData.data.forEach((row, i) => (row.index = (i + 1).toString()))
    sampleItems.value = batchData.data
    if (!batchData.batch_matches_info) return
    matchSamples.value = batchData.batch_matches_info?.match_samples
    matchCompounds.value = batchData.batch_matches_info?.match_compounds
    matchIons.value = batchData.batch_matches_info?.match_ions
  }

  async function loadBatchTargets(batchId) {
    const batchTargetsData = await getBatchTargets(batchId)

    let newTargetCollections = batchTargetsData.target_collections

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
    targetCompounds.value = batchTargetsData.target_compounds
    targetIons.value = batchTargetsData.target_ions
    targetIsotopes.value = batchTargetsData.target_isotopes
  }

  async function reload(batch = null) {
    const targetStore = useTargetsStore()
    const batchToLoad = batch ?? active.value
    if (!batchToLoad) return

    await unload(false)
    const batchToLoadId = batchToLoad.sample_batch_id
    await load(batchToLoadId)
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
        setCollectionSelection({
          collectionId: activeCollectionId,
          selectionValue: 2
        })
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
    sampleItems.value = null
    // targets
    targetCollections.value = null
    targetCompounds.value = null
    targetIons.value = null
    targetIsotopes.value = null
    // matches
    matchSamples.value = null
    matchCompounds.value = null
    matchIons.value = null
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
    return await api.request({
      httpMethod: 'getBatch',
      requestData: batchId,
      errorMessage: `Failed to load batch.`
    })
  }

  async function getBatchSamplesData(batchId) {
    const targetStore = useTargetsStore()
    const alarmsList = targetStore.alarmsList

    const body = {
      sample_batch_id: batchId,
      batch_matches_info: true,
      sort: 'sample_item_utc_created',
      alarms_list: alarmsList
    }

    return await api.request({
      httpMethod: 'getAllSamples',
      requestData: body,
      errorMessage: `Failed to load batch samples data.`
    })
  }

  async function getBatchTargets(batchId) {
    const targetStore = useTargetsStore()
    const alarmsList = targetStore.alarmsList

    const reqData = {
      batchId,
      body: {
        alarms_list: alarmsList
      }
    }
    const batchTargetsData = await api.request({
      httpMethod: 'getBatchTargets',
      requestData: reqData,
      errorMessage: `Failed to get batch targets.`
    })

    return batchTargetsData.data
  }

  async function importSamplesToBatch(data) {
    const body = {
      sample_items: data.sample_items
    }
    const batch = data.batch
    return await api.process({
      httpMethod: 'importSamplesToBatch',
      requestData: { batch, body },
      successMessage: `Sample batch "${batch.sample_batch_name}" import started`,
      errorMessage: `Failed to import sample batch "${batch.sample_batch_name}". Please try again.`
    })
  }
  async function createBatch(newBatch) {
    return await api.process({
      httpMethod: 'createBatch',
      requestData: newBatch,
      successMessage: `Sample batch "${newBatch.sample_batch_name}" created successfully!`,
      errorMessage: `Failed to create sample batch "${newBatch.sample_batch_name}". Please try again.`
    })
  }
  async function updateBatch(newBatch) {
    const batchId = newBatch.sample_batch_id
    const body = newBatch
    return await api.process({
      httpMethod: 'updateBatch',
      requestData: { batchId, body },
      successMessage: `Sample batch "${newBatch.sample_batch_name}"  updated successfully!`,
      errorMessage: `Failed to update sample batch "${newBatch.sample_batch_name}". Please try again.`
    })
  }

  async function deleteBatch(batch) {
    return await api.process({
      httpMethod: 'deleteBatch',
      requestData: batch,
      progressNotificationPayload: {
        action: 'delete',
        type: 'batch',
        message: `Deleting batch "${batch.sample_batch_name}", please wait`
      }
    })
  }
  async function copyBatch(batchCopyData) {
    const batchId = batchCopyData.sample_batch_id
    const body = {
      workspace_id: batchCopyData.workspace_id,
      sample_batch_name: batchCopyData.sample_batch_name,
      sample_batch_description: batchCopyData.sample_batch_description
    }
    return await api.process({
      httpMethod: 'copySampleBatch',
      requestData: { batchId, body },
      progressNotificationPayload: {
        action: 'copy',
        type: 'batch',
        message: `Copying batch "${batchCopyData.sample_batch_name}" to the workspace "${batchCopyData.workspace_name}", please wait`
      }
    })
  }

  async function batchExportPeakData(sampleBatch) {
    return await api.process({
      httpMethod: 'batchExportPeakData',
      requestData: sampleBatch,
      progressNotificationPayload: {
        action: 'export',
        type: 'peaks',
        message: `Exporting peak data for batch "${sampleBatch.sample_batch_name}", please wait.`
      }
    })
  }

  async function rematchBatch(batch = null) {
    const batchId = batch?.sample_batch_id ?? active.value.sample_batch_id
    const body = {}
    try {
      await api.http.rematchBatch({ batchId, body })
    } catch (error) {
      // TODO_error_handling and use handleApiRequest for start notification
      console.error(`Failed to rematch batch.`, error)
      const userErrorMessage = `${error.message}. ${error}`
      const notificationStore = useNotificationStore()
      notificationStore.showGeneralNotification({
        notification: 'error',
        message: userErrorMessage
      })
    }
  }

  // backend notifications
  async function onSampleBatchReload() {
    await reload()
  }

  // selection
  async function batchToggle(batch) {
    const workspaceStore = useWorkspaceStore()
    workspaceStore.batches.forEach((row) => (row.selection = 0))
    const active_batch_id = active.value?.sample_batch_id ?? null
    if (active_batch_id == batch.sample_batch_id) {
      unload()
    } else {
      load(batch.sample_batch_id)
      workspaceStore.batches
        .filter((row) => row.sample_batch_id == batch.sample_batch_id)
        .forEach((row) => (row.selection = 2))
    }
  }
  // Sample selection toggling
  async function sampleItemFocus(sampleItemFocused) {
    const sampleItemFocusedId = sampleItemFocused.sample_item_id
    sampleItems.value
      .filter((row) => row.sample_item_id != sampleItemFocusedId && row.selection == 3)
      .forEach((item) => (item.selection = 0))
    sampleItemFocused = sampleItem.value(sampleItemFocusedId)
    const sampleStore = useSampleStore()
    switch (sampleItemFocused.selection) {
      case 0:
      case 2:
        // Focus
        sampleItemFocused.selection = 3
        await sampleStore.load(sampleItemFocused)
        break
      case 3:
        // Unfocus
        sampleItemFocused.selection = 0
        await sampleStore.unload(null)
        break
    }
  }
  async function sampleItemToggle(sampleItemToggled) {
    const sampleItemToggledId = sampleItemToggled.sample_item_id
    sampleItems.value
      .filter((row) => row.sample_item_id != sampleItemToggledId && row.selection == 2)
      .forEach((item) => (item.selection = 0))
    sampleItemToggled = sampleItem.value(sampleItemToggledId)
    switch (sampleItemToggled.selection) {
      case 0:
        // Select
        sampleItemToggled.selection = 2
        break
      case 2:
        // Unselect
        sampleItemToggled.selection = 0
        break
      case 3:
        // Stay focused
        sampleItemToggled.selection = 3
        break
    }
  }
  // target collection selection toggling
  async function targetCollectionToggle(targetCollectionToggled) {
    const targetCollectionToggledId = targetCollectionToggled.target_collection_id
    targetCollections.value
      ?.filter((row) => row.target_collection_id != targetCollectionToggledId && row.selection == 2)
      .forEach((collection) => (collection.selection = 0))
    targetCollectionToggled = targetCollection.value(targetCollectionToggledId)
    switch (targetCollectionToggled.selection) {
      case 0:
        setCollectionSelection({
          collectionId: targetCollectionToggledId,
          selectionValue: 2
        })
        break
      case 2:
        // Unselect
        setCollectionSelection({
          collectionId: targetCollectionToggledId,
          selectionValue: 0
        })
        break
      case 3:
        // Stay focused
        setCollectionSelection({
          collectionId: targetCollectionToggledId,
          selectionValue: 3
        })
        break
    }
    // Dispatch to targets module to update selection there as well
    const targetStore = useTargetsStore()
    targetStore.updateCollectionSelection({
      collectionId: targetCollectionToggledId,
      selectionValue: targetCollectionToggled.selection
    })
    // Dispatch to sample module if sample is active to update selection there as well
    const sampleStore = useSampleStore()
    if (sampleStore.matchCollections?.length > 0) {
      sampleStore.updateCollectionSelection({
        collectionId: targetCollectionToggledId,
        selectionValue: targetCollectionToggled.selection
      })
    }
  }

  return {
    // state
    active,
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
    getSampleItems,
    getTargetCollections,
    getTargetCompounds,
    getTargetIons,
    getTargetIsotopes,
    sampleItem,
    targetCollection,
    targetCompound,
    targetIon,
    targetIsotope,
    sampleItemsSelected,
    sampleItemFocused,
    targetCollectionsSelected,
    targetCompoundsSelected,
    targetIonsSelected,
    targetIsotopesSelected,
    // actions
    setCollectionSelection,
    load,
    loadBatch,
    loadBatchSamplesData,
    loadBatchTargets,
    reload,
    unload,
    resetParams,
    unpackParams,
    getBatch,
    getBatchSamplesData,
    getBatchTargets,
    importSamplesToBatch,
    createBatch,
    updateBatch,
    deleteBatch,
    copyBatch,
    batchExportPeakData,
    rematchBatch,
    onSampleBatchReload,
    batchToggle,
    sampleItemFocus,
    sampleItemToggle,
    targetCollectionToggle
  }
})
