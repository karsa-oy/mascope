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

import { BaseMatchTag } from '@/lib/base'
import {
  DialogSampleBatchOp,
  DialogSampleItemOp,
  DialogCalibration,
  useSampleBatchDeleteDialog
} from '@/lib/dialogs'

import { beautifySnakeCase } from '@/lib/utils'
import { batchExportCsv } from '@/lib/table'
import { useApp } from '@/stores'

const confirm = useConfirm()

const app = useApp()

const dialog = reactive({
  batch: {
    op: null,
    delete: useSampleBatchDeleteDialog(),
    calibration: false
  },
  item: {
    op: null,
    calibration: false
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

const batchContextMenu = ref()
const itemContextMenu = ref()

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
  () => app.data.sample.focused,
  (selected) => {
    if (selected?.sample_item_id == app.data.sample.focused?.sample_item_id) {
      return
    }
    if (selected) {
      app.data.sample.focus(selected)
    } else {
      app.data.sample.unfocus()
    }
  }
)
watch(
  () => app.data.sample.focused,
  (active) => {
    if (active?.sample_item_id == app.data.sample.focused?.sample_item_id) {
      return
    }
    if (active) {
      app.data.sample.focused = active
    } else {
      app.data.sample.focused = null
    }
  }
)
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

const menu = computed(() => ({
  batch: [
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
      command: () => copy(batch.context),
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
          header: 'Export batch peak data',
          message: `Export peak data for batch "${app.data.batch.focused.sample_batch_name}"?`,
          acceptIcon: 'pi pi-file-export',
          acceptLabel: 'Export',
          accept: () => {
            if (app.data.batch.focused?.sample_batch_id == batch.context.sample_batch_id) {
              app.data.batch.exportPeaks(app.data.batch.focused)
            } else {
              app.data.batch.focused = batch.context
              pending.peakExport = true
            }
          },
          rejectLabel: 'Cancel',
          rejectIcon: 'pi pi-times'
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
  ],
  item: [
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
      command: () => copy(item.context)
    },
    {
      label: `Delete sample`,
      icon: 'pi pi-trash',
      command: () => {
        confirm.require({
          header: `Deleting sample '${item.context.sample_item_name}'`,
          message: `Delete sample '${item.context.sample_item_name}'
          from batch "${app.data.batch.focused.sample_batch_name}"?`,
          icon: 'pi pi-exclamation-triangle',
          rejectProps: {
            label: 'Cancel',
            severity: 'secondary'
          },
          acceptProps: {
            icon: 'pi pi-trash',
            label: 'Delete',
            severity: 'danger'
          },
          accept: async () => {
            // unload if necessary
            if (item.context.sample_item_id == app.data.sample.focused?.sample_item_id) {
              app.data.sample.unfocus()
            }
            await app.data.sample.delete(item.context)
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
    }
  ]
}))

async function copy(context) {
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

const batchPreventDefault = (event) => {
  batchContextMenu.value.show(event.originalEvent)
}
const itemPreventDefault = (event) => {
  itemContextMenu.value.show(event.originalEvent)
}

/**
 * Watches for changes in the focused sample and updates the match visualization accordingly.
 *
 * This watcher reacts whenever `app.data.sample.focused` changes:
 * - Scenario 1: Match Tab is active (app.ui.matchVisualized.ion is set)
 *   - If a new sample is focused and there's an ion currently visualized in the Match tab,
 *     the function retrieves the corresponding data from `app.ui.matchVisualized.ion`.
 *   - The match visualization is then updated with the new sample ID,  visualised ion ID, collection ID, and its filter parameters.
 *
 * - Scenario 2: Target selection in Target Browser (app.ui.matchVisualized.ion is inactive):
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
  async (newFocusedSample) => {
    if (!newFocusedSample) {
      // If no sample is focused, unset the match visualization
      return app.ui.matchVisualized.unset({ target: false })
    }

    const { instrument, sample_item_id: sampleId } = newFocusedSample
    let ionId = null
    let collectionId = null
    let filterParams = null

    if (app.ui.matchVisualized.ion) {
      // Scenario 1: Match Tab is Active, use currently visualized ion details
      ;({ target_ion_id: ionId, target_collection_id: collectionId } = app.ui.matchVisualized.ion)
      filterParams = app.ui.matchVisualized.ion?.filter_params?.[instrument] || null
    } else if (app.data.match.ion.selected.length > 0) {
      // Scenario 2: Match Tab is Not Active but a Match Ion is Selected
      const selectedIon = app.data.match.ion.selected[0]
      ionId = app.data.match.ion.focusedId
      collectionId = app.data.match.collection.focusedId
      filterParams = selectedIon?.filter_params?.[instrument] || null
    } else if (app.data.match.compound.selected.length > 0) {
      // Scenario 2: Match Tab is Not Active but a Match Compound is Selected
      const ion = app.data.match.ion.list?.find(
        (ion) => ion.target_compound_id === app.data.match.compound.focusedId
      )
      if (ion) {
        ionId = ion.target_ion_id
        collectionId = app.data.match.collection.focusedId
        filterParams = ion.filter_params?.[instrument] || null
      }
    }

    if (ionId && collectionId) {
      // Set the match visualization with the new sample ID, ion ID, collection ID, and filter params
      await app.ui.matchVisualized.set({
        sampleId: sampleId,
        ionId,
        collectionId,
        params: filterParams
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
        v-tooltip.top="'Edit batch fields'"
        icon="pi pi-sliders-h"
        severity="secondary"
        text
        size="small"
        @click="
          (event) => {
            batchOptionsPopover.toggle(event)
          }
        "
      />
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
            batchPreventDefault(e)
            parseClipboard()
          }
        "
        sortField="sample_batch_utc_created"
        :sortOrder="-1"
        size="small"
      >
        <Column header="Batch" field="sample_batch_name" sortable>
          <template #body="{ data }">
            <span
              :class="`pi pi-chevron-${data.sample_batch_id in batch.expanded ? 'down' : 'right'}`"
              style="font-size: smaller; margin-right: 0.5rem"
            />
            {{ data.sample_batch_name }}
          </template>
        </Column>
        <template #expansion="{ data }">
          <div v-if="!app.data.sample.loading" style="min-height: 2rem">
            <DataTable
              v-if="data.children.length > 0 && app.data.batch.focused"
              :value="data.children"
              v-model:selection="app.data.sample.focused"
              selectionMode="single"
              :metaKeySelection="false"
              dataKey="sample_item_id"
              sortField="index"
              contextMenu
              v-model:contextMenuSelection="item.context"
              @rowContextmenu="
                (e) => {
                  itemPreventDefault(e)
                  parseClipboard()
                }
              "
              size="small"
              reorderableColumns
              stateStorage="local"
              :stateKey="`mascope-sample-table-${data.sample_batch_id}`"
            >
              <Column field="match_score" sortable class="match-column">
                <template #header>
                  <span class="pi pi-verified" />
                </template>
                <template #body="{ data }">
                  <BaseMatchTag
                    :row="data"
                    :tooltip="`Peak intensity: ${formatter.format(data?.sample_peak_area_sum)}`"
                  />
                </template>
              </Column>

              <template v-for="{ field, label, kind } in batchSelectedColumns" :key="field">
                <Column v-if="kind == 'standard'" :field="field" :header="label" sortable />
                <Column
                  v-if="kind == 'custom'"
                  field="sample_item_attributes"
                  :header="label"
                  sortable
                >
                  <template #body="{ data }">
                    <span>{{ data.sample_item_attributes[field] }}</span>
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
      <ContextMenu ref="batchContextMenu" :model="menu.batch" />
      <ContextMenu ref="itemContextMenu" :model="menu.item" />
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
  <DialogSampleBatchOp v-model:action="dialog.batch.op" :batch="batch.context" />
  <DialogSampleItemOp v-model:action="dialog.item.op" :item="item.context" />
  <DialogCalibration v-model:visible="dialog.batch.calibration" :context="batch.context" />
  <DialogCalibration v-model:visible="dialog.item.calibration" :context="item.context" />
</template>

<style scoped>
:deep(.p-listbox-list-container) {
  height: 180px;
}
</style>
