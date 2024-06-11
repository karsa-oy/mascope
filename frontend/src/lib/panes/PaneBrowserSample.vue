<script setup>
import { useConfirm } from 'primevue/useconfirm'

import { ref, reactive, computed, watch, watchEffect } from 'vue'

import ScrollPanel from 'primevue/scrollpanel'
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
import { useWorkspaceStore, useSampleStore, useBatchStore, useFocusedMatch } from '@/stores'

const confirm = useConfirm()

const workspaceStore = useWorkspaceStore()
const sampleStore = useSampleStore()
const batchStore = useBatchStore()
const focusedMatch = useFocusedMatch()

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
  selected: null,
  context: null,
  pasted: null
})
const item = reactive({
  selected: null,
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
  computed(() => batch.selected),
  async (selected) => {
    if (selected) {
      const batchId = batch.selected.sample_batch_id
      batch.expanded = { [batchId]: true }
      await batchStore.load(selected.sample_batch_id)
      handlePending()
    } else {
      batch.expanded = {}
      batchStore.unload()
    }
  }
)
function handlePending() {
  if (pending.batchExport) {
    batchExportCsv()
    pending.batchExport = false
  }
  if (pending.peakExport) {
    batchStore.exportPeaks(batchStore.active)
    pending.peakExport = false
  }
}
watch(
  computed(() => item.selected),
  (selected) => {
    if (selected?.sample_item_id == sampleStore.active?.sample_item_id) {
      return
    }
    if (selected) {
      sampleStore.load(selected)
    } else {
      sampleStore.unload()
    }
  }
)
watch(
  computed(() => sampleStore.active),
  (active) => {
    if (active?.sample_item_id == item.selected?.sample_item_id) {
      return
    }
    if (active) {
      item.selected = active
    } else {
      item.selected = null
    }
  }
)
watch(
  computed(() => workspaceStore.active),
  () => {
    batch.selected = null
    item.selected = null
  }
)

const formatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
})

// computed
const tree = computed(() => {
  return workspaceStore.batches.map((batch) => ({
    ...batch,
    children:
      batchStore.sampleItems?.filter((sample) => sample.sample_batch_id == batch.sample_batch_id) ??
      []
  }))
})

const menu = computed(() => ({
  batch: [
    {
      label: 'Paste item',
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
      command: () => {
        if (batch.selected?.sample_batch_id == batch.context.sample_batch_id) {
          batchExportCsv()
        } else {
          batch.selected = batch.context
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
          message: `Export peak data for batch "${batchStore.active.sample_batch_name}"?`,
          acceptIcon: 'pi pi-file-export',
          acceptLabel: 'Export',
          accept: () => {
            if (batch.selected?.sample_batch_id == batch.context.sample_batch_id) {
              batchStore.exportPeaks(batchStore.active)
            } else {
              batch.selected = batch.context
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
      command: () => batchStore.rematchBatch(batch.context),
      visible: batch.context !== null
    }
  ],
  item: [
    {
      label: 'Paste item',
      icon: 'pi pi-clipboard',
      visible: item.pasted !== null,
      command: () => pasteItem(item.context)
    },
    {
      separator: true,
      visible: item.pasted !== null
    },
    {
      label: `Edit item`,
      icon: 'pi pi-file-edit',
      command: () => {
        dialog.item.op = 'update'
      }
    },
    {
      label: 'Copy item',
      icon: 'pi pi-copy',
      command: () => copy(item.context)
    },
    {
      label: `Delete item`,
      icon: 'pi pi-trash',
      command: () => {
        confirm.require({
          header: 'Deleting item',
          message: `Delete sample "${item.context.sample_item_name}"
          from batch "${batchStore.active.sample_batch_name}"?`,
          acceptIcon: 'pi pi-trash',
          acceptLabel: 'Delete',
          accept: async () => {
            const itemId = item.context.sample_item_id
            // unload if necessary
            if (itemId == sampleStore.active?.sample_item_id) {
              sampleStore.unload()
            }
            await sampleStore.deleteSampleItem(itemId)
          },
          rejectLabel: 'Cancel',
          rejectIcon: 'pi pi-times'
        })
      }
    },
    { separator: true },
    {
      label: `Recalibrate item`,
      icon: 'pi pi-replay',
      command: () => {
        dialog.item.calibration = true
      }
    },
    {
      label: `Rematch item`,
      icon: 'pi pi-replay',
      command: async () => {
        await sampleStore.matchSampleRematch(item.context)
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
    await batchStore.copyBatch({
      sample_batch_id: batch.pasted.sample_batch_id,
      workspace_id: workspaceStore.active.workspace_id,
      sample_batch_name: generateCopyName(batch.pasted.sample_batch_name),
      sample_batch_description: batch.pasted.sample_batch_description
    })
  }
}
async function pasteItem(context) {
  if (item.pasted) {
    await sampleStore.copySample({
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

watchEffect(async () => {
  if (item.selected) {
    await focusedMatch.load({
      sampleId: item.selected.sample_item_id
    })
  } else {
    focusedMatch.unload({ target: false })
  }
})

const batchColumnTab = ref('All')
const inferType = (field) => {
  const withField = batchStore.sampleItems.filter((item) => field in item)
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
      batchStore.sampleItems
        ?.map((item) => Object.keys(item ?? {}))
        .flat()
        .filter((field) => field !== 'sample_item_attributes')
    )
  ].map((field) => ({ field, kind: 'standard' }))
  const custom = [
    ...new Set(
      batchStore.sampleItems?.map((item) => Object.keys(item?.sample_item_attributes ?? {})).flat()
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
    `mascope-sample-columns-${batch.selected.sample_batch_id}`,
    JSON.stringify(cols)
  )
})
watch(
  computed(() => batch.selected),
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

<template v-if="workspaceStore.batches">
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
        v-tooltip="'Create batch'"
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
    <ScrollPanel>
      <DataTable
        :value="tree"
        v-model:expandedRows="batch.expanded"
        dataKey="sample_batch_id"
        v-model:selection="batch.selected"
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
          <template #body="slotProps">
            <span
              :class="`pi pi-chevron-${slotProps.data.sample_batch_id in batch.expanded ? 'down' : 'right'}`"
              style="font-size: smaller; margin-right: 0.5rem"
            />
            {{ slotProps.data.sample_batch_name }}
          </template>
        </Column>
        <Column style="width: 4rem">
          <template #body="slotProps">
            <Button
              v-if="slotProps.data.sample_batch_id in batch.expanded"
              icon="pi pi-ellipsis-h"
              severity="secondary"
              text
              @click="
                (event) => {
                  batchOptionsPopover.show(event)
                }
              "
              v-tooltip.right="'Batch options'"
            />
            <Popover ref="batchOptionsPopover" contentStyle="height: fit-content;">
              <div class="row" style="margin-bottom: 0.5rem">
                <SelectButton
                  v-model="batchColumnTab"
                  :options="['All', 'Selected']"
                  :allowEmpty="false"
                />
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
          </template>
        </Column>
        <template #expansion="slotProps">
          <div v-if="!batchStore.loading" style="min-height: 2rem">
            <DataTable
              v-if="slotProps.data.children.length > 0"
              :value="slotProps.data.children"
              v-model:selection="item.selected"
              selectionMode="single"
              :metaKeySelection="false"
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
              :stateKey="`mascope-sample-table-${slotProps.data.sample_batch_id}`"
            >
              <Column field="match_score" sortable class="match-column">
                <template #header>
                  <span class="pi pi-verified" />
                </template>
                <template #body="{ data }">
                  <BaseMatchTag
                    v-if="data.matched == 1"
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
    </ScrollPanel>
  </Panel>
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
