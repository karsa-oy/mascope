<script setup>
import { computed } from 'vue'

import BaseBrowser from '@/components/base/BaseBrowser.vue'

import {
  useWorkspaceStore,
  useSampleStore,
  useBatchStore,
  useVisualizationStore,
  useModalStore
} from '@/stores'

const workspaceStore = useWorkspaceStore()
const sampleStore = useSampleStore()
const batchStore = useBatchStore()
const visualizationStore = useVisualizationStore()
const modalStore = useModalStore()

const noop = () => {}

const formatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
})

const contextMenuIcon = computed(() => {
  if (batchStore.targetCollectionsSelected.length === 1) return 'menu'
  if (workspaceStore.sampleBatchesSelected.length === 1) return 'dots-horizontal'
  if (workspaceStore.sampleBatchesSelected.length !== 1) return 'plus'
  return null
})
const targetCollectionRows = computed(() =>
  sampleStore.active && sampleStore.matchCollections
    ? sampleStore.matchCollections
    : batchStore.targetCollections
)
const targetCompoundRows = computed(() => {
  if (!sampleStore.active || !sampleStore.matchCompounds) {
    return batchStore.targetCompounds
  }
  return batchStore.targetCompounds.map((targetCompound) => {
    const matchCompound = sampleStore.matchCompounds.find(
      (mc) => mc.target_compound_id === targetCompound.target_compound_id
    )

    return matchCompound ? { ...targetCompound, ...matchCompound } : targetCompound
  })
})
const targetIonRows = computed(() => {
  if (!sampleStore.active || !sampleStore.matchIons) {
    return batchStore.targetIons
  }
  return batchStore.targetIons.map((targetIon) => {
    const matchIon = sampleStore.matchIons.find(
      (mi) => mi.target_ion_id === targetIon.target_ion_id
    )

    return matchIon ? { ...targetIon, ...matchIon } : targetIon
  })
})
const targetIsotopeRows = computed(() => {
  if (!sampleStore.active || !sampleStore.matchIsotopes) {
    return batchStore.targetIsotopes
  }

  const matchIsotopeIds = new Set(sampleStore.matchIsotopes.map((mi) => mi.target_isotope_id))

  return batchStore.targetIsotopes
    .filter(({ target_isotope_id }) => matchIsotopeIds.has(target_isotope_id))
    .map((targetIsotope) => {
      const matchIsotope = sampleStore.matchIsotopes.find(
        (mis) => mis.target_isotope_id === targetIsotope.target_isotope_id
      )

      return matchIsotope ? { ...targetIsotope, ...matchIsotope } : targetIsotope
    })
})
const targetLevels = computed(() => {
  let hidden = sampleStore.matchIsotopes ? false : true
  return [
    {
      name: 'Collection',
      slug: 'target_collection',
      cols: [
        {
          field: 'target_collection_name',
          label: 'Collection',
          width: '30%'
        },
        {
          field: 'target_collection_description',
          label: 'Description',
          width: '60%'
        },
        {
          field: 'match_score',
          label: 'Score',
          width: '10%',
          displayMatchScore: true,
          hidden,
          tooltip: (row) => {
            return {
              'Peak intensity': formatter.format(row.sample_peak_area_sum)
            }
          }
        }
      ],
      rows: targetCollectionRows.value,
      defaultSort: ['match_score', 'desc'],
      detailsIcon: 'default',
      rowClick: batchStore.targetCollectionToggle
    },
    {
      name: 'Compound',
      slug: 'target_compound',
      cols: [
        {
          field: 'target_compound_formula',
          label: 'Compound',
          width: '45%'
        },
        { field: 'target_compound_name', label: '', width: '45%' },
        {
          field: 'match_score',
          label: 'Score',
          width: '10%',
          hidden,
          tooltip: (row) => {
            return {
              'Peak intensity': formatter.format(row.sample_peak_area_sum)
            }
          }
        }
      ],
      rows: targetCompoundRows.value,
      defaultSort: ['match_score', 'desc'],
      detailsIcon: 'default',
      rowClick: noop
    },
    {
      name: 'Ion',
      slug: 'target_ion',
      cols: [
        { field: 'target_ion_formula', label: 'Ion', width: '45%' },
        { field: 'ionMech', label: '', width: '45%' },
        {
          field: 'match_score',
          label: 'Score',
          width: '10%',
          hidden,
          tooltip: (row) => {
            return {
              'Peak intensity': formatter.format(row.sample_peak_area_sum)
            }
          }
        }
      ],
      rows: targetIonRows.value,
      defaultSort: ['match_score', 'desc'],
      detailsIcon: 'default',
      rowClick: noop
    },
    {
      name: 'Isotope',
      slug: 'target_isotope',
      cols: [
        { field: 'mz', label: 'Isotope', width: '45%' },
        { field: 'relative_abundance', label: 'Fraction', width: '45%' },
        {
          field: 'match_score',
          label: 'Score',
          width: '10%',
          hidden,
          tooltip: (row) => {
            return {
              'Peak intensity': formatter.format(row.sample_peak_area)
            }
          }
        }
      ],
      rows: targetIsotopeRows.value,
      defaultSort: ['mz', 'asc'],
      detailsIcon: sampleStore.active ? 'chart-bell-curve' : null,
      detailsOpen: sampleStore.active ? matchScoreTagClicked : null,
      rowClick: noop
    }
  ]
})
const menu = computed(() => {
  // target collection
  let createCollectionButton = {
    label: 'Create target collection',
    onClick: collectionCreate
  }
  let updateCollectionButton = {
    label: 'Update target collection',
    onClick: collectionUpdate
  }
  let deleteCollectionButton = {
    label: 'Delete target collection',
    onClick: collectionDelete
  }
  let copySelectedCollectionToOtherBatchesButton = {
    label: 'Manage selected collection batches',
    onClick: manageCollectionBatches
  }
  let editBatchCollectionsButton = {
    label: 'Edit collections of selected batch',
    onClick: editBatchCollections
  }

  if (
    batchStore.targetCollectionsSelected.length == 0 &&
    workspaceStore.sampleBatchesSelected.length == 1
  ) {
    return [editBatchCollectionsButton, createCollectionButton]
  }
  if (batchStore.targetCollectionsSelected.length == 0) {
    return [createCollectionButton]
  }
  if (batchStore.targetCollectionsSelected.length == 1) {
    return [
      editBatchCollectionsButton,
      createCollectionButton,
      updateCollectionButton,
      copySelectedCollectionToOtherBatchesButton,
      deleteCollectionButton
    ]
  }
  return null
})

function manageCollectionBatches() {
  modalStore.state.targetCollectionOpProps = {
    action: 'manageCollectionBatches'
  }
  modalStore.activate({
    modal: 'targetCollectionOp'
  })
}
function editBatchCollections() {
  modalStore.state.sampleBatchOpProps = {
    action: 'editBatchCollections'
  }
  modalStore.activate({
    modal: 'sampleBatchOp'
  })
}
function collectionCreate() {
  modalStore.state.targetCollectionOpProps = {
    action: 'create'
  }
  modalStore.activate({
    modal: 'targetCollectionOp'
  })
}
function collectionDelete() {
  modalStore.state.targetCollectionOpProps = {
    action: 'delete'
  }
  modalStore.activate({
    modal: 'targetCollectionOp'
  })
}
function collectionUpdate() {
  modalStore.state.targetCollectionOpProps = {
    action: 'update'
  }
  modalStore.activate({
    modal: 'targetCollectionOp'
  })
}
async function ionShow({ ionId, collectionId }) {
  const sampleId = sampleStore.active.sample_item_id

  // pass the ion specific filter params if acvailable to the loadSampleIon function
  const filterParams =
    sampleStore.matchIons.filter((ion) => ion.target_ion_id === ionId)[0]?.filter_params[
      sampleStore.active.instrument
    ] || null

  await visualizationStore.load({ sampleId, ionId, collectionId, filterParams })

  modalStore.activate({
    modal: 'sampleItemTargetIon'
  })
}
function matchScoreTagClicked(row) {
  const ionId =
    // Ion or isotope tag clicked
    row?.target_ion_id ??
    // Compound tag clicked -> fetch corresponding ion id
    sampleStore.matchIons.filter((ion) => ion.target_compound_id === row.target_compound_id)[0]
      ?.target_ion_id ??
    // Collection tag clicked
    null
  if (!ionId) return
  const collectionId = row?.target_collection_id
  ionShow({ ionId, collectionId })
}
</script>

<template>
  <section>
    <base-browser
      v-if="targetCollectionRows"
      name="Targets"
      :levels="targetLevels"
      :menu="menu"
      :contextMenuIcon="contextMenuIcon"
      @tagClicked="matchScoreTagClicked"
    >
    </base-browser>
  </section>
</template>
