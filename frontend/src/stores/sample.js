import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

import { api } from '@/api'
import { useMzFit } from '@/lib/mzFit'

import { useNotification } from './notification'
import { useBatchStore } from './batch'
import { useTargetsStore } from './targets'

export const useSampleStore = defineStore('sample', () => {
  const notification = useNotification()

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
    if (!sample) return
    // reset if previous sample loaded
    if (active.value) await unload({ deactivate: false })
    const sampleItemId = sample.sample_item_id
    api.emit('subscribe', sampleItemId)
    active.value = sample
    await loadSampleData(sampleItemId)
  }

  async function loadSampleData(sampleItemId) {
    // Check if matches exist for the given sampleItemId
    const sampleMatches = (
      await api.request.read({
        method: 'getAllMatches',
        body: {
          sample_item_id: sampleItemId
        }
      })
    )?.data
    // TODO sample matched property is already exist in the sample object. Should delete this and check related code
    matched.value = sampleMatches.length > 0 ? 1 : 0

    // Get detailed sample data
    const targetsStore = useTargetsStore()
    const alarms_list = targetsStore.alarmsList

    const sampleData = (
      await api.request.read({
        method: 'getSample',
        body: {
          sampleId: sampleItemId,
          body: {
            alarms_list
          }
        }
      })
    )?.data
    if (!sampleData) return
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

  async function unload({ deactivate } = { deactivate: true }) {
    if (!active.value) return
    api.emit('unsubscribe', active.value.sample_item_id)
    if (deactivate) {
      active.value = null
    }
    matched.value = null
    matchCollections.value = null
    matchCompounds.value = null
    matchIons.value = null
    matchIsotopes.value = null
  }

  async function reload(sample = null) {
    const sampleToLoad = sample ?? active.value
    if (sampleToLoad) {
      await unload()
      await load(sampleToLoad)
    }
  }

  notification.on('create_sample_item', async ({ data }) => {
    const batchStore = useBatchStore()
    await batchStore.reload()
    const sampleItem = batchStore.sampleItem(data?.sample_item_id)
    await load(sampleItem)
  })()

  async function create(sample) {
    return await api.request.create({
      method: 'createSampleItem',
      body: sample
    })
  }
  async function process(sample) {
    const mzFit = useMzFit()
    const targetsStore = useTargetsStore()
    return await api.request.process({
      method: 'processSampleItem',
      body: {
        sample,
        mz_calibration_params: mzFit.params,
        alarms: targetsStore.alarmsList
      }
    })
  }
  async function update(sample) {
    const sampleId = sample.sample_item_id
    const body = sample
    return await api.request.update({
      method: 'updateSampleItem',
      body: { sampleId, body }
    })
  }
  async function deleteSampleItem(sampleId) {
    return await api.request.delete({
      method: 'deleteSampleItem',
      body: { sampleId }
    })
  }
  async function matchSampleCompute(sample) {
    const sampleId = sample.sample_item_id
    return await api.request.process({
      method: 'matchSampleCompute',
      body: { sampleId }
    })
  }
  async function matchSampleRematch(sample) {
    const sampleId = sample.sample_item_id
    return await api.request.process({
      method: 'rematchSample',
      body: { sampleId }
    })
  }

  async function copySample(sample) {
    return await api.request.process({
      method: 'copySampleItem',
      body: {
        sampleId: sample.sample_item_id,
        body: {
          sample_batch_id: sample.sample_batch_id,
          sample_item_name: sample.sample_item_name
        }
      }
    })
  }

  // Attribute templates
  const template = {
    create: async (newTemplate) => {
      return await api.request.create({
        method: 'createAttributeTemplate',
        body: newTemplate
      })
    },
    update: async (template) => {
      const templateId = template.attribute_template_id
      const body = template
      return await api.request.update({
        method: 'updateAttributeTemplate',
        body: { templateId, body }
      })
    },
    delete: async (template) => {
      const templateId = template.attribute_template_id
      const templateName = template.name
      return await api.request.delete({
        method: 'deleteAttributeTemplate',
        body: { templateId, templateName }
      })
    }
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
    create,
    process,
    update,
    deleteSampleItem,
    matchSampleCompute,
    matchSampleRematch,
    copySample,
    template,
    updateCollectionSelection
  }
})
