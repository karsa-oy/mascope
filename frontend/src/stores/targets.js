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

  const getCollection = computed(
    () => (targetCollectionId) =>
      getAllCollections.value.find((row) => row.target_collection_id == targetCollectionId) ?? null
  )
  // TODO_configuration possible collection types
  const collectionTypes = computed(() => ['TARGETS', 'DIAGNOSTICS', 'CALIBRANTS'])
  // get alarm_mode list
  const alarmsList = computed(() =>
    [
      [alarmTargets.value, 'TARGETS'],
      [alarmDiagnostics.value, 'DIAGNOSTICS'],
      [alarmCalibrants.value, 'CALIBRANTS']
    ]
      .filter((val) => val[0])
      .map((val) => val[1])
  )
  const targetCollectionsSelected = computed(() => {
    return targetCollectionsAll.value?.filter((row) => row.selection >= 2) ?? []
  })

  // actions

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
    if (!collections) return
    collections = collections.map((collection) => {
      return { ...collection, selection: 0 }
    })
    targetCollectionsAll.value = collections
  }

  async function loadAllCompounds() {
    const compounds = await getAllTargetCompounds()
    if (!compounds) return
    targetCompoundsAll.value = compounds
  }

  async function loadActiveCollection(collectionId) {
    const collection = await getTargetCollection(collectionId)
    if (!collection) return
    activeCollection.value = collection
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
  // http client endpoints
  async function getAllTargetCollections() {
    const collections = await api.request.read({
      method: 'getAllTargetCollections'
    })
    return collections?.data ?? null
  }

  async function getTargetCollection(collectionId) {
    return await api.request.read({
      method: 'getTargetCollection',
      body: collectionId
    })
  }

  async function getAllTargetCompounds(params = {}) {
    const compounds = await api.request.read({
      method: 'getAllTargetCompounds',
      body: params
    })
    return compounds?.data ?? null
  }

  async function createCollection(collection) {
    return await api.request.create({
      method: 'createTargetCollection',
      body: collection
    })
  }

  async function updateCollection(collection) {
    const collectionId = collection.target_collection_id
    const body = collection
    return await api.request.update({
      method: 'updateTargetCollection',
      body: { collectionId, body }
    })
  }

  async function deleteCollection({ collectionId, collectionName, deleteOrphanCompounds }) {
    activeCollection.value = {} // TODO check if this should be null or call unload
    return await api.request.delete({
      method: 'deleteTargetCollection',
      body: { collectionId, collectionName, deleteOrphanCompounds }
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
    targetCollectionsAll.value = targetCollectionsAll.value.map((coll) =>
      coll.target_collection_id === collectionId ? { ...coll, selection: selectionValue } : coll
    )

    // If a collection is selected, fetch its details
    const selectedCollections =
      targetCollectionsAll.value?.filter((row) => row.selection >= 2) ?? []
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
