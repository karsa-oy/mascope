<script setup>
import { useConfirm } from 'primevue/useconfirm'

import { ref, reactive, computed, watch } from 'vue'

import Panel from 'primevue/panel'
import Button from 'primevue/button'
import TabMenu from 'primevue/tabmenu'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import ProgressSpinner from 'primevue/progressspinner'
import ContextMenu from 'primevue/contextmenu'
import Popover from 'primevue/popover'
import Listbox from 'primevue/listbox'
import SelectButton from 'primevue/selectbutton'

import { generateCopyName } from '@/api'

import { BaseMatchTag, BaseCopyableField } from '@/lib/base'
import {
  DialogBatchOp,
  DialogSampleOp,
  DialogCalibration,
  DialogInstrumentFunction,
  useBatchDeleteDialog
} from '@/lib/dialogs'

import { beautifySnakeCase } from '@/lib/utils'
import { batchExportCsv } from '@/lib/table'
import { useApp } from '@/stores'

const confirm = useConfirm()

const app = useApp()

const dialog = reactive({
  batch: {
    op: null,
    delete: useBatchDeleteDialog(),
    calibration: false
  },
  item: {
    op: null,
    calibration: false,
    instrumentFunction: false
  }
})

const batch = reactive({
  expanded: {},
  context: null,
  pasted: null
})
const item = reactive({
  context: null,
  pasted: null
})

const pending = reactive({
  batchExport: false,
  peakExport: false
})

const batchOptionsPopover = ref()

watch(
  () => app.data.batch.focused,
  async (selected) => {
    if (selected) {
      const batchId = app.data.batch.focused.sample_batch_id
      batch.expanded = { [batchId]: true }
      app.data.batch.focus(selected)
      await handlePending()
    } else {
      batch.expanded = {}
      app.data.batch.unfocus()
    }
  }
)
watch(
  () => Object.keys(batch.expanded).length == 0,
  async (collapsed) => {
    if (collapsed) {
      app.data.sample.unfocus()
    }
  }
)
async function handlePending() {
  if (pending.batchExport) {
    await batchExportCsv()
    pending.batchExport = false
  }
  if (pending.peakExport) {
    await app.data.batch.exportPeaks(app.data.batch.focused)
    pending.peakExport = false
  }
}
watch(
  () => app.data.workspace.focused,
  () => {
    app.data.batch.focused = null
    app.data.sample.focused = null
  }
)

const formatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
})

// computed
const tree = computed(() => {
  return app.data.batch.list.map((batch) => ({
    ...batch,
    children:
      app.data.sample.list?.filter((sample) => sample.sample_batch_id == batch.sample_batch_id) ??
      []
  }))
})

// batch context menu

// component ref
const batchContextMenu = ref()

// prevent default event handling
const handleBatchRightClick = (event) => {
  batchContextMenu.value.show(event.originalEvent)
}

const batchMenuEntries = computed(() => [
  {
    label: 'Paste sample',
    icon: 'pi pi-clipboard',
    command: () => pasteItem(batch.context),
    visible: item.pasted !== null && batch.context !== null
  },
  {
    label: 'Paste batch',
    icon: 'pi pi-clipboard',
    command: () => pasteBatch(),
    visible: batch.pasted !== null
  },
  {
    separator: true,
    visible: (batch.pasted !== null || item.pasted !== null) && batch.context !== null
  },
  {
    label: 'Edit batch',
    icon: 'pi pi-pen-to-square',
    command: () => {
      dialog.batch.op = 'update'
    },
    visible: batch.context !== null
  },
  {
    label: 'Edit batch targets',
    icon: 'pi pi-bullseye',
    command: () => {
      dialog.batch.op = 'update_targets'
    },
    visible: batch.context !== null
  },
  {
    label: 'Copy batch',
    icon: 'pi pi-copy',
    command: () => copyContext(batch.context),
    visible: batch.context !== null
  },
  {
    label: 'Delete batch',
    icon: 'pi pi-trash',
    command: () => dialog.batch.delete(batch.context),
    visible: batch.context !== null
  },
  { separator: true, visible: batch.context !== null },
  {
    label: 'Export batch',

    icon: 'pi pi-file-export',
    command: async () => {
      if (app.data.batch.focused?.sample_batch_id == batch.context.sample_batch_id) {
        await batchExportCsv()
      } else {
        app.data.batch.focused = batch.context
        pending.batchExport = true
      }
    },
    visible: batch.context !== null
  },
  {
    label: 'Export peaks',
    icon: 'pi pi-file-export',
    command: () => {
      confirm.require({
        icon: 'pi pi-info-circle',
        header: 'Export batch peak data',
        message: `Export peak data for batch "${app.data.batch.focused.sample_batch_name}"?`,
        accept: () => {
          if (app.data.batch.focused?.sample_batch_id == batch.context.sample_batch_id) {
            app.data.batch.exportPeaks(app.data.batch.focused)
          } else {
            app.data.batch.focused = batch.context
            pending.peakExport = true
          }
        },
        acceptProps: {
          icon: 'pi pi-file-export',
          label: 'Export'
        },
        rejectProps: {
          icon: 'pi pi-times',
          label: 'Cancel',
          severity: 'secondary'
        }
      })
    },
    visible: batch.context !== null
  },
  { separator: true, visible: batch.context !== null },
  {
    label: `Recalibrate batch`,
    icon: 'pi pi-replay',
    command: () => {
      dialog.batch.calibration = true
    },
    visible: batch.context !== null
  },
  {
    label: 'Rematch batch',
    icon: 'pi pi-replay',
    command: () => app.data.batch.rematch(batch.context),
    visible: batch.context !== null
  }
])

// sample context menu

// component ref
const sampleContextMenu = ref()

// prevent default event handling
const handleSampleRightClick = (event) => {
  // disable context menu for multiselection
  if (app.data.sample.focused) {
    sampleContextMenu.value.show(event.originalEvent)
  }
}

const sampleMenuEntries = computed(() => [
  {
    label: 'Paste sample',
    icon: 'pi pi-clipboard',
    visible: item.pasted !== null,
    command: () => pasteItem(item.context)
  },
  {
    separator: true,
    visible: item.pasted !== null
  },
  {
    label: `Edit sample`,
    icon: 'pi pi-file-edit',
    command: () => {
      dialog.item.op = 'update'
    }
  },
  {
    label: 'Copy sample',
    icon: 'pi pi-copy',
    command: () => copyContext(item.context)
  },
  {
    label: `Delete sample`,
    icon: 'pi pi-trash',
    command: () => {
      confirm.require({
        icon: 'pi pi-exclamation-triangle',
        header: `Deleting sample '${item.context.sample_item_name}'`,
        message: `Delete sample '${item.context.sample_item_name}'
          from batch "${app.data.batch.focused.sample_batch_name}"?`,
        accept: async () => {
          // unload if necessary
          if (item.context.sample_item_id == app.data.sample.focused?.sample_item_id) {
            app.data.sample.unfocus()
          }
          await app.data.sample.delete(item.context)
        },
        acceptProps: {
          icon: 'pi pi-trash',
          label: 'Delete',
          severity: 'danger'
        },
        rejectProps: {
          label: 'Cancel',
          severity: 'secondary'
        }
      })
    }
  },
  { separator: true },
  {
    label: `Recalibrate sample`,
    icon: 'pi pi-replay',
    command: () => {
      dialog.item.calibration = true
    }
  },
  {
    label: `Rematch sample`,
    icon: 'pi pi-replay',
    command: async () => {
      await app.data.sample.rematch(item.context)
    }
  },
  {
    label: `Compute all peaks`,
    icon: 'pi pi-wave-pulse',
    command: async () => {
      await app.data.peak.computeAll(item.context)
    }
  },
  {
    label: `Refit instrument functions`,
    icon: 'pi pi-wave-pulse',
    command: () => {
      dialog.item.instrumentFunction = true
    }
  }
])

// copy-paste

async function copyContext(context) {
  const clipboard = JSON.stringify(context)
  try {
    await navigator.clipboard.writeText(clipboard)
  } catch (err) {
    console.warn(err)
  }
}
async function parseClipboard() {
  let clipboard, pasted
  try {
    clipboard = await navigator.clipboard.readText()
    pasted = JSON.parse(clipboard)
  } catch (err) {
    return
  }
  if (pasted?.sample_batch_id) {
    if (pasted?.sample_item_id) {
      item.pasted = pasted
      batch.pasted = null
    } else {
      batch.pasted = pasted
      item.pasted = null
    }
  }
}
async function pasteBatch() {
  if (batch.pasted) {
    await app.data.batch.copy({
      sample_batch_id: batch.pasted.sample_batch_id,
      workspace_id: app.data.workspace.focused.workspace_id,
      sample_batch_name: generateCopyName(batch.pasted.sample_batch_name),
      sample_batch_description: batch.pasted.sample_batch_description
    })
  }
}
async function pasteItem(context) {
  if (item.pasted) {
    await app.data.sample.copy({
      sample_item_id: item.pasted.sample_item_id,
      sample_batch_id: context.sample_batch_id,
      sample_item_name: generateCopyName(item.pasted.sample_item_name)
    })
  }
}

/**
 * Watches for changes in the focused sample and updates the match visualization accordingly.
 *
 * This watcher reacts whenever `app.data.sample.focused` changes:
 * - Scenario 1: Match Tab is active (app.data.match.visualized.ion is set)
 *   - If a new sample is focused and there's an ion currently visualized in the Match tab,
 *     the function retrieves the corresponding data from `app.data.match.visualized.ion`.
 *   - The match visualization is then updated with the new sample ID,  visualised ion ID, collection ID, and its filter parameters.
 *
 * - Scenario 2: Target selection in Target Browser (app.data.match.visualized.ion is inactive):
 *   - If no ion is currently visualized but there is a selected ion in the Target browser,
 *     it retrieves the focused ion and the appropriate filter parameters from `app.data.match.ion.selected`.
 *   - If a compound is selected instead, it finds the corresponding ion from the loaded ions and retrieves its filter parameters.
 *   - The match visualization is then triggered with the selected sample, ion, and selected collection details.
 *
 * - Unsetting the Match Visualization:
 *   - If no sample is focused, the match visualization tab is cleared by calling `unset`.
 *
 * @param {Object|null} newFocusedSample - The new sample that has been focused, or null if no sample is focused.
 */
watch(
  () => app.data.sample.focused,
  async (focusedSample) => {
    if (!focusedSample) {
      // If no sample is focused, unset the match visualization
      return app.data.match.visualized.unset({
        cacheTarget: true
      })
    }

    const { instrument, sample_item_id: sampleId } = focusedSample
    let ionId = null
    let collectionId = app.data.match.collection.focusedId

    if (app.data.match.visualized.ion) {
      // match visualized
      ;({ target_ion_id: ionId, target_collection_id: collectionId } =
        app.data.match.visualized.ion)
    } else if (app.data.match.ion.focused) {
      // no match visualized but match ion focused
      ionId = app.data.match.ion.focusedId
    } else if (app.data.match.compound.focused) {
      // no match visualized but match compound focused
      const ionId = app.data.match.ion.list?.find(
        (ion) => ion.target_compound_id === app.data.match.compound.focusedId
      )?.target_ion_id
    }

    if (ionId && collectionId) {
      // Set the match visualization with the new sample ID, ion ID, collection ID, and filter params
      await app.data.match.visualized.set({
        sampleId,
        ionId,
        collectionId
      })
    }
  }
)

const batchColumnTab = ref('All')
const inferType = (field) => {
  const withField = app.data.sample.list.filter((item) => field in item)
  const types = [
    ...new Set(withField.map((item) => (item[field] ? typeof item[field] : 'null')))
  ].filter((type) => type !== 'null')
  return types.length == 1 ? types[0] : 'unknown'
}
const createLabel = (field) => {
  const custom = {
    index: '#',
    sample_item_name: 'Item',
    filter_id: 'Filter'
  }
  if (field in custom) {
    return custom[field]
  } else {
    return beautifySnakeCase(field)
  }
}
const batchDefaultColumns = [
  { field: 'sample_item_name', kind: 'standard', label: 'Item', type: 'string' },
  { field: 'index', kind: 'standard', label: '#', type: 'string' },
  { field: 'filter_id', kind: 'standard', label: 'Filter', type: 'string' }
]
const batchAvailableColumns = computed(() => {
  const standard = [
    ...new Set(
      app.data.sample.list
        ?.map((item) => Object.keys(item ?? {}))
        .flat()
        .filter((field) => field !== 'sample_item_attributes')
    )
  ].map((field) => ({ field, kind: 'standard' }))
  const custom = [
    ...new Set(
      app.data.sample.list?.map((item) => Object.keys(item?.sample_item_attributes ?? {})).flat()
    )
  ].map((field) => ({ field, kind: 'custom' }))
  return [...standard, { field: 'time', kind: 'custom', label: 'Time' }, ...custom]
    .map(({ field, kind }) => ({
      field,
      kind,
      label: createLabel(field),
      type: kind == 'custom' ? 'string' : inferType(field)
    }))
    .filter(({ type }) => type !== 'object')
})

const batchSelectedColumns = ref(batchDefaultColumns)

watch(batchSelectedColumns, (cols) => {
  localStorage.setItem(
    `mascope-sample-columns-${app.data.batch.focused.sample_batch_id}`,
    JSON.stringify(cols)
  )
})
watch(
  () => app.data.batch.focused,
  (selected) => {
    if (selected) {
      const storedColumns = localStorage.getItem(
        `mascope-sample-columns-${selected.sample_batch_id}`
      )
      batchSelectedColumns.value = storedColumns ? JSON.parse(storedColumns) : batchDefaultColumns
    }
  }
)
</script>

<template v-if="app.data.batch.list">
  <Panel
    class="browser"
    style="border: none"
    @contextmenu.prevent="
      (event) => {
        parseClipboard()
        if (batch.pasted !== null) {
          batch.context = null
          batchContextMenu.show(event)
        }
      }
    "
  >
    <template #header>
      <TabMenu :model="[{ label: 'Samples', icon: 'pi pi-tags' }]" />
    </template>
    <template #icons>
      <Button
        v-tooltip.top="'Create batch'"
        label="Create batch"
        class="hiddenlabel"
        icon="pi pi-plus"
        text
        size="small"
        @click="
          () => {
            dialog.batch.op = 'create'
          }
        "
      />
    </template>
    <div class="scroller">
      <DataTable
        :value="tree"
        v-model:expandedRows="batch.expanded"
        dataKey="sample_batch_id"
        v-model:selection="app.data.batch.focused"
        selectionMode="single"
        :metaKeySelection="false"
        contextMenu
        v-model:contextMenuSelection="batch.context"
        @rowContextmenu="
          (e) => {
            handleBatchRightClick(e)
            parseClipboard()
          }
        "
        sortField="sample_batch_utc_created"
        :sortOrder="-1"
        size="small"
      >
        <Column header="Batch" field="sample_batch_name" sortable>
          <template #body="{ data }">
            <div class="row" style="justify-content: flex-start">
              <span
                :class="`pi pi-chevron-${data.sample_batch_id in batch.expanded ? 'down' : 'right'}`"
                style="font-size: smaller; margin-right: 0.5rem"
              />
              <BaseCopyableField :field="data.sample_batch_name" />
            </div>
          </template>
        </Column>
        <Column>
          <template #body="{ data }">
            <Button
              v-if="data.sample_batch_id in batch.expanded"
              v-tooltip.top="'Edit batch fields'"
              icon="pi pi-ellipsis-h"
              severity="secondary"
              text
              size="small"
              @click="
                (event) => {
                  event.stopPropagation()
                  batchOptionsPopover.toggle(event)
                }
              "
            />
          </template>
        </Column>
        <template #expansion="{ data }">
          <!-- samples -->
          <div v-if="!app.data.sample.loading" style="min-height: 2rem">
            <DataTable
              v-if="data.children.length > 0 && app.data.batch.focused"
              :value="data.children"
              v-model:selection="app.data.sample.selected"
              selectionMode="multiple"
              :metaKeySelection="true"
              dataKey="sample_item_id"
              sortField="index"
              contextMenu
              v-model:contextMenuSelection="item.context"
              @rowContextmenu="
                (e) => {
                  handleSampleRightClick(e)
                  parseClipboard()
                }
              "
              size="small"
              reorderableColumns
              stateStorage="local"
              :stateKey="`mascope-sample-table-${data.sample_batch_id}`"
              @stateRestore="
                () => {
                  // don't restore selection
                  app.data.sample.unfocus()
                }
              "
            >
              <Column field="match_score" sortable class="match-column">
                <template #header>
                  <span class="pi pi-verified" />
                </template>
                <template #body="{ data }">
                  <BaseMatchTag
                    :row="data"
                    :tooltip="`Peak intensity sum: ${formatter.format(data?.sample_peak_area_sum)}`"
                  />
                </template>
              </Column>

              <template v-for="{ field, label, kind } in batchSelectedColumns" :key="field">
                <Column v-if="kind == 'standard'" :field="field" :header="label" sortable>
                  <template #body="{ data }">
                    <span class="field">
                      <BaseCopyableField :field="data[field]" />
                    </span>
                  </template>
                </Column>
                <Column
                  v-if="kind == 'custom'"
                  field="sample_item_attributes"
                  :header="label"
                  sortable
                >
                  <template #body="{ data }">
                    <BaseCopyableField :field="data.sample_item_attributes[field]" />
                  </template>
                </Column>
              </template>
            </DataTable>
            <i v-else style="padding-left: 3em; margin-top: 1rem; line-height: 2rem">
              Empty - no sample items
            </i>
          </div>
          <div class="spinner" v-else><ProgressSpinner strokeWidth="5px" />loading...</div>
        </template>
      </DataTable>
      <ContextMenu ref="batchContextMenu" :model="batchMenuEntries" />
      <ContextMenu ref="sampleContextMenu" :model="sampleMenuEntries" />
    </div>
  </Panel>
  <Popover ref="batchOptionsPopover" contentStyle="height: fit-content;">
    <div class="row" style="margin-bottom: 0.5rem">
      <SelectButton v-model="batchColumnTab" :options="['All', 'Selected']" :allowEmpty="false" />
      <Button
        icon="pi pi-replay"
        severity="secondary"
        label="Reset"
        iconPos="right"
        text
        @click="batchSelectedColumns = batchDefaultColumns"
        v-tooltip.right="'Reset columns'"
      />
    </div>
    <Listbox
      v-model="batchSelectedColumns"
      :options="
        batchAvailableColumns.filter(({ field }) =>
          batchColumnTab == 'Selected'
            ? batchSelectedColumns.map(({ field }) => field).includes(field)
            : true
        )
      "
      multiple
      optionLabel="label"
      filter
      dataKey="field"
      style="height: 230px"
    />
  </Popover>
  <DialogBatchOp v-model:action="dialog.batch.op" :batch="batch.context" />
  <DialogSampleOp v-model:action="dialog.item.op" :item="item.context" />
  <DialogCalibration v-model:visible="dialog.batch.calibration" :context="batch.context" />
  <DialogCalibration v-model:visible="dialog.item.calibration" :context="item.context" />
  <DialogInstrumentFunction
    v-model:visible="dialog.item.instrumentFunction"
    :sample="item.context"
  />
</template>

<style scoped>
:deep(.p-listbox-list-container) {
  height: 180px;
}
</style>
