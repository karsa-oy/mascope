import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

import { api } from '@/api'

export const useTargetsStore = defineStore('targets', () => {
  const activeCollection = ref(null)
  // alarm_mode
  const alarmTargets = ref(true)
  const alarmDiagnostics = ref(false)
  const alarmCalibrants = ref(false)
  // all targets
  const targetCollectionsAll = ref(null)
  const targetCompoundsAll = ref(null)

  // getters

  const getAllCollections = computed(() => targetCollectionsAll.value ?? [])
  const getAllCompounds = computed(() => targetCompoundsAll.value ?? [])
  const getTargetsCollections = computed(
    () =>
      targetCollectionsAll.value?.filter(
        (collection) => collection.target_collection_type === 'TARGETS'
      ) ?? []
  )
  const getCalibrantsCollections = computed(
    () =>
      targetCollectionsAll.value?.filter(
        (collection) => collection.target_collection_type === 'CALIBRANTS'
      ) ?? []
  )
  const getDiagnosticsCollections = computed(
    () =>
      targetCollectionsAll.value?.filter(
        (collection) => collection.target_collection_type === 'DIAGNOSTICS'
      ) ?? []
  )
  const getCollection = computed(
    () => (targetCollectionId) =>
      getAllCollections.value.find((row) => row.target_collection_id == targetCollectionId) ?? null
  )
  // TODO_configuration possible collection types
  const collectionTypes = computed(() => ['TARGETS', 'DIAGNOSTICS', 'CALIBRANTS'])
  // get alarm_mode list
  const alarmsList = computed(() =>
    [
      [alarmTargets, 'TARGETS'],
      [alarmDiagnostics, 'DIAGNOSTICS'],
      [alarmCalibrants, 'CALIBRANTS']
    ]
      .filter((val) => val[0])
      .map((val) => val[1])
  )
  const targetCollectionsSelected = computed(() => {
    return targetCollectionsAll.value?.filter((row) => row.selection >= 2) ?? []
  })

  // actions

  function setCollectionAllSelection({ collectionId, selectionValue }) {
    const collection = targetCollectionsAll.value.find(
      (coll) => coll.target_collection_id === collectionId
    )
    if (collection) {
      collection.selection = selectionValue
    }
  }

  // data loading
  async function load(collectionId = null) {
    if (activeCollection.value) await unload()
    await loadAllCollections()
    await loadAllCompounds()
    if (!collectionId) return
    await loadActiveCollection(collectionId)
  }

  async function loadAllCollections() {
    let collections = await getAllTargetCollections()

    collections = collections.map((collection) => {
      return { ...collection, selection: 0 }
    })
    targetCollectionsAll.value = collections
  }

  async function loadAllCompounds() {
    targetCompoundsAll.value = await getAllTargetCompounds()
  }

  async function loadActiveCollection(collectionId) {
    activeCollection.value = await getTargetCollection(collectionId)
  }

  async function reload() {
    const collectionToLoadId = activeCollection.value?.target_collection_id ?? null
    await load(collectionToLoadId)
    if (!collectionToLoadId) return
    await updateCollectionSelection({
      collectionId: collectionToLoadId,
      selectionValue: 2
    })
  }

  async function unload() {
    targetCollectionsAll.value = null
    targetCompoundsAll.value = null
    if (!activeCollection.value) return
    activeCollection.value = null
  }

  function processSpreadsheetInput(rows) {
    // process the spreadsheet input to check if compounds already exist
    let existingCompounds = []
    let notExistingCompounds = []
    let processedFormulas = new Set() // Set to track processed compound formulas
    rows.forEach((row) => {
      // Skip processing if this formula has already been processed
      if (processedFormulas.has(row.target_compound_formula)) {
        return
      }

      const existingCompound = targetCompoundsAll.value.find(
        (compound) => compound.target_compound_formula === row.target_compound_formula
      )

      if (existingCompound) {
        //  If an existing compound is found, add it to existingCompounds
        existingCompounds.push(existingCompound)
      } else {
        // If no existing compound is found, add the row to notExistingCompounds
        notExistingCompounds.push(row)
      }

      // Mark this formula as processed
      processedFormulas.add(row.target_compound_formula)
    })
    return { existingCompounds, notExistingCompounds }
  }

  // http client endpoints
  async function getAllTargetCollections() {
    const collections = await api.request({
      httpMethod: 'getAllTargetCollections',
      errorMessage: `Failed to load all target collections.`
    })
    return collections.data
  }

  async function getTargetCollection(collectionId) {
    return await api.request({
      httpMethod: 'getTargetCollection',
      requestData: collectionId,
      errorMessage: `Failed to get target collection.`
    })
  }

  async function getAllTargetCompounds(params = {}) {
    const compounds = await api.request({
      httpMethod: 'getAllTargetCompounds',
      requestData: params,
      errorMessage: `Failed to load all target compounds.`
    })
    return compounds.data
  }

  async function createCollection(collection) {
    return await api.process({
      httpMethod: 'createTargetCollection',
      requestData: collection,
      successMessage: `Target collection ${collection.target_collection_name} created successfully!`,
      errorMessage: `Failed to create target collection ${collection.target_collection_name}. Please try again.`
    })
  }

  async function updateCollection(collection) {
    const collectionId = collection.target_collection_id
    const body = collection
    return await api.process({
      httpMethod: 'updateTargetCollection',
      requestData: { collectionId, body },
      successMessage: `Target collection ${collection.target_collection_name} updated successfully!`,
      errorMessage: `Failed to update target collection ${body.target_collection_name}. Please try again.`
    })
  }

  async function deleteCollection({ collectionId, collectionName, deleteOrphanCompounds }) {
    activeCollection.value = {} // TODO check if this should be null or call unload
    return await api.process({
      httpMethod: 'deleteTargetCollection',
      requestData: { collectionId, collectionName, deleteOrphanCompounds },
      successNotificationType: 'deleted',
      successMessage: `Target collection ${collectionName} was deleted successfully!`,
      errorMessage: `Failed to delete target collection ${collectionName}. Please try again.`
    })
  }

  // backend notifications
  async function onTargetsAllReload() {
    reload()
  }

  // selection
  async function updateCollectionSelection({ collectionId, selectionValue }) {
    // Only one collection can be selected at a time
    targetCollectionsAll.value
      .filter((coll) => coll.target_collection_id !== collectionId && coll.selection === 2)
      .forEach((coll) => (coll.selection = 0))

    // Update the selected collection's selection value
    setCollectionAllSelection({
      collectionId,
      selectionValue
    })

    // If a collection is selected, fetch its details
    const selectedCollections = targetCollectionsSelected.value
    if (selectionValue === 2 && selectedCollections.length === 1) {
      await loadActiveCollection(collectionId)
    } else {
      activeCollection.value = null
    }
  }

  return {
    // state
    activeCollection,
    alarmTargets,
    alarmDiagnostics,
    alarmCalibrants,
    targetCollectionsAll,
    targetCompoundsAll,
    // getters
    getAllCollections,
    getAllCompounds,
    getTargetsCollections,
    getCalibrantsCollections,
    getDiagnosticsCollections,
    getCollection,
    collectionTypes,
    alarmsList,
    targetCollectionsSelected,
    // actions
    load,
    loadAllCollections,
    loadAllCompounds,
    loadActiveCollection,
    reload,
    unload,
    processSpreadsheetInput,
    getAllTargetCollections,
    getTargetCollection,
    getAllTargetCompounds,
    createCollection,
    updateCollection,
    deleteCollection,
    onTargetsAllReload,
    updateCollectionSelection
  }
})
