<script setup>
import { computed } from 'vue'
import { dialog } from '@ntohq/buefy-next'

import BaseBrowser from './BaseBrowser.vue'

import table from '@/lib/table'

import { useWorkspaceStore, useSampleStore, useBatchStore, useModalStore } from '@/stores'

const workspaceStore = useWorkspaceStore()
const sampleStore = useSampleStore()
const batchStore = useBatchStore()
const modalStore = useModalStore()

const formatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
})

// computed
const contextMenuIcon = computed(() => {
  return batchActiveCount.value == 0 ? 'plus' : 'dots-horizontal'
})
const sampleLevels = computed(() => {
  let hidden = batchStore.active ? false : true
  return [
    {
      name: 'Batch',
      slug: 'sample_batch',
      cols: [{ field: 'sample_batch_name', label: 'Batch', width: '90%' }],
      detailsIcon: 'none',
      rows: workspaceStore.batches,
      rowClick: batchStore.batchToggle,
      opened: openedBatch
    },
    {
      name: 'Item',
      slug: 'sample_item',
      cols: [
        { field: 'index', label: '#', width: '5%' },
        { field: 'sample_item_name', label: 'Item', width: '75%' },
        { field: 'datetime', label: 'Datetime', width: '0%', hidden: true },
        { field: 'filter_id', label: 'Filter ID', width: '10%' },
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
      rows: batchStore.sampleItems,
      detailsIcon: 'none',
      rowClick: itemSelect,
      opened: []
    }
  ]
})
const batchActiveCount = computed(() => {
  return batchStore.active ? 1 : 0
})
const menu = computed(() => {
  // sample batch
  let createBatchButton = {
    label: 'Create sample batch',
    onClick: batchCreate
  }
  let deleteBatchButton = {
    label: 'Delete sample batch',
    onClick: batchDelete
  }
  let exportBatchButton = {
    label: 'Export sample batch',
    onClick: batchExport
  }
  let exportBatchPeaksButton = {
    label: 'Export peak data',
    onClick: batchPeakExport
  }
  let updateBatchButton = {
    label: 'Update sample batch',
    onClick: batchUpdate
  }
  let copyBatchButton = {
    label: 'Copy selected batch',
    onClick: batchCopy
  }
  let rematchBatchButton = {
    label: 'Rematch selected batch (debug)',
    onClick: batchStore.rematchBatch
  }
  let batchButtons =
    batchActiveCount.value == 0
      ? [createBatchButton]
      : [
          updateBatchButton,
          deleteBatchButton,
          exportBatchButton,
          exportBatchPeaksButton,
          copyBatchButton,
          rematchBatchButton
        ]
  // sample items
  let updateItemButton = {
    label: `Update sample item`,
    onClick: itemUpdate
  }
  let deleteItemButton = {
    label: `Delete sample item`,
    onClick: itemDelete
  }
  let copyItemButton = {
    label: 'Copy selected sample item',
    onClick: itemCopy
  }
  let rematchItemButton = {
    label: `Rematch selected sample (debug)`,
    onClick: itemRematch
  }
  let itemButtons = batchStore.sampleItemFocused
    ? [updateItemButton, deleteItemButton, copyItemButton, rematchItemButton]
    : []
  // menu
  return batchStore.sampleItemFocused ? itemButtons : batchButtons
})
const openedBatch = computed(() => {
  return batchStore.active
    ? workspaceStore.batches.filter(
        (batch) => batch.sample_batch_id == batchStore.active.sample_batch_id
      )
    : []
})

// methods
function batchCreate() {
  modalStore.sampleBatchOpProps = {
    action: 'create'
  }
  modalStore.activate({
    modal: 'sampleBatchOp'
  })
}
function batchDelete() {
  modalStore.sampleBatchOpProps = {
    action: 'delete',
    batch: batchStore.active
  }
  modalStore.activate({
    modal: 'sampleBatchOp'
  })
}
function batchExport() {
  const batchCols = [
    { field: 'field', label: 'Batch' },
    { field: 'value', label: '' }
  ]
  let batchRows = [
    { field: 'Name', value: batchStore.active.sample_batch_name },
    {
      field: 'Description',
      value: batchStore.active.sample_batch_description
    },
    { field: 'Workspace', value: workspaceStore.active.workspace_name },
    { field: '', value: '' },
    {
      field: 'Target collections',
      value: batchStore.targetCollections.map((row) => row.target_collection_name).join(', ')
    },
    { field: '', value: '' },
    { field: 'Parameters', value: '' }
  ]
  const batchParams = {
    ...batchStore.buildParams
  }
  Object.entries(batchParams).forEach(([key, val]) =>
    batchRows.push({
      field: key.replaceAll('_', ' '),
      value: JSON.stringify(val)
    })
  )
  const sampleItemCols = [
    { field: 'sample_item_name', label: 'Sample name' },
    { field: 'filename', label: 'Filename' },
    { field: 'datetime', label: 'Datetime' },
    { field: 'sample_item_type', label: 'Sample type' },
    { field: 'tic', label: 'TIC' },
    { field: 'filter_id', label: 'Filter ID' },
    { field: 'match_score', label: 'Match score' }
  ]
  const matchCompoundCols = [
    { field: 'sample_item_name', label: 'Sample name' },
    { field: 'filename', label: 'Filename' },
    { field: 'sample_item_type', label: 'Sample type' },
    { field: 'target_compound_name', label: 'Compound name' },
    { field: 'target_compound_formula', label: 'Compound formula' },
    { field: 'sample_peak_area_sum', label: 'Sample peak intensity' },
    {
      field: 'sample_peak_interference_max',
      label: 'Sample peak interference'
    },
    { field: 'match_score', label: 'Match score' }
  ]
  const matchIonCols = [
    { field: 'sample_item_name', label: 'Sample name' },
    { field: 'filename', label: 'Filename' },
    { field: 'sample_item_type', label: 'Sample type' },
    { field: 'target_compound_name', label: 'Compound name' },
    { field: 'target_compound_formula', label: 'Compound formula' },
    { field: 'target_ion_mechanism', label: 'Ionization mechanism' },
    { field: 'target_ion_formula', label: 'Ion formula' },
    { field: 'sample_peak_area_sum', label: 'Sample peak intensity' },
    {
      field: 'sample_peak_interference_sum',
      label: 'Sample peak interference'
    },
    { field: 'match_score', label: 'Match score' }
  ]
  const datetimestamp = new Date().toJSON().slice(0, -5).replace(/[-:]/g, '')
  const filename = `${datetimestamp}_${batchStore.active.sample_batch_name.replaceAll(
    ' ',
    '_'
  )}.xlsx`
  // Extend batchMatchCompounds with sample_item_type
  const extendedMatchCompounds = batchStore.matchCompounds.map((compound) => {
    const sampleItem = batchStore.sampleItems.find(
      (item) => item.sample_item_id === compound.sample_item_id
    )
    return {
      ...compound,
      sample_item_type: sampleItem?.sample_item_type || null
    }
  })
  // Extend batchMatchIons with sample_item_type, target_compound_name, and target_compound_formula
  const extendedMatchIons = batchStore.matchIons.map((ion) => {
    const sampleItem = batchStore.sampleItems.find(
      (item) => item.sample_item_id === ion.sample_item_id
    )
    const targetCompound = batchStore.targetCompounds.find(
      (compound) => compound.target_compound_id === ion.target_compound_id
    )
    return {
      ...ion,
      sample_item_type: sampleItem?.sample_item_type || null,
      target_compound_name: targetCompound?.target_compound_name || null,
      target_compound_formula: targetCompound?.target_compound_formula || null
    }
  })
  table.toSpreadsheet(filename, [
    {
      name: 'Batch',
      rows: batchRows,
      cols: batchCols
    },
    {
      name: 'Samples',
      rows: batchStore.sampleItems,
      cols: sampleItemCols
    },
    {
      name: 'Match compounds',
      rows: extendedMatchCompounds,
      cols: matchCompoundCols
    },
    {
      name: 'Match ions',
      rows: extendedMatchIons,
      cols: matchIonCols
    }
  ])
}
function batchPeakExport() {
  dialog.confirm({
    title: 'Export batch peak data',
    message: `Export peak data for batch "${batchStore.active.sample_batch_name}"?`,
    confirmText: 'Export',
    onConfirm: () => {
      batchStore.batchExportPeakData(batchStore.active)
    }
  })
}
function batchUpdate() {
  modalStore.sampleBatchOpProps = {
    action: 'update',
    batch: batchStore.active
  }
  modalStore.activate({
    modal: 'sampleBatchOp'
  })
}
function batchCopy() {
  modalStore.sampleBatchOpProps = {
    action: 'copy',
    batch: batchStore.active
  }
  modalStore.activate({
    modal: 'sampleBatchOp'
  })
}
async function itemUpdate() {
  modalStore.sampleItemAttributesSaveProps = {
    action: 'update',
    sampleItemRecordToLoad: batchStore.sampleItemFocused
  }
  modalStore.activate({ modal: 'sampleItemAttributesSave' })
}
async function itemRematch() {
  await sampleStore.matchSampleRematch(sampleStore.active)
}
function itemDelete() {
  dialog.confirm({
    title: 'Deleting item',
    message: `Delete sample "${batchStore.sampleItemFocused.sample_item_name}"
          from batch "${batchStore.active.sample_batch_name}"?`,
    confirmText: 'Delete',
    onConfirm: async () => {
      const itemId = batchStore.sampleItemFocused.sample_item_id
      // defocus
      batchStore.itemFocus(batchStore.sampleItemFocused)
      await sampleStore.deleteSampleItem(itemId)
    }
  })
}
function itemSelect(row) {
  batchStore.itemToggle(row)
  batchStore.itemFocus(row)
}
function itemCopy() {
  modalStore.sampleItemOverviewProps = {
    action: 'copy',
    sample: batchStore.sampleItemFocused
  }
  modalStore.activate({
    modal: 'sampleItemOverview'
  })
}
</script>

<template>
  <base-browser
    name="Samples"
    :levels="sampleLevels"
    :menu="menu"
    :contextMenuIcon="contextMenuIcon"
  >
  </base-browser>
</template>
