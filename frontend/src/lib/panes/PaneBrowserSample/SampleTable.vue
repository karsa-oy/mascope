<script setup>
import { ref, reactive, computed } from 'vue'

import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import ProgressSpinner from 'primevue/progressspinner'
import ContextMenu from 'primevue/contextmenu'
import { useConfirm } from 'primevue/useconfirm'

import { api, generateCopyName } from '@/api'

import { BaseMatchTag, BaseCopyableField } from '@/lib/base'
import { DialogSampleOp, DialogCalibration } from '@/lib/dialogs'
import { clone } from '@/lib/utils'
import { useApp } from '@/stores'

const confirm = useConfirm()
const app = useApp()

const props = defineProps({
  batch: {
    type: Object,
    required: true
  }
})

const config = defineModel('config')

const emit = defineEmits(['contextMenu'])

const samples = computed(() => props.batch?.children ?? [])

const dialog = reactive({
  op: null,
  calibration: false,
  instrumentConfig: false
})

const sample = reactive({
  context: null,
  pasted: null
})

const formatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
})

// CONTEXT MENU

// component ref
const contextMenuRef = ref()

const isSample = (item) => item.sample_item_id && item.sample_batch_id && item.sample_item_name

// prevent default event handling
const onContextMenuClick = async (event) => {
  // disable context menu for multiselection
  if (app.data.sample.selectedIds.includes(sample.context?.sample_item_id)) {
    contextMenuRef.value.show(event.originalEvent)
    emit('contextMenu', contextMenuRef.value)
  } else {
    contextMenuRef.value.hide()
  }
  // parse clipboard
  let clipboard, pasted
  try {
    clipboard = await navigator.clipboard.readText()
    pasted = JSON.parse(clipboard)
  } catch (err) {
    return
  }
  const valid = pasted?.every(isSample) ?? false
  if (valid) {
    sample.pasted = pasted
  }
}

const contextMenuEntries = computed(() => {
  const multiselecting = app.data.sample.selected.length > 1
  const s = multiselecting ? 's' : ''
  return [
    {
      label: `Paste sample${sample.pasted?.length > 1 ? 's' : ''}`,
      icon: 'pi pi-clipboard',
      visible: sample.pasted !== null,
      command: async () => {
        if (sample.pasted.length > 0) {
          await app.data.sample.copy({
            sample_item_ids: sample.pasted.map((s) => s.sample_item_id),
            sample_batch_id: props.batch.sample_batch_id
          })
        }
      }
    },
    {
      separator: true,
      visible: sample.pasted !== null
    },
    {
      label: `Edit sample`,
      icon: 'pi pi-file-edit',
      visible: app.data.sample.focused !== null,
      command: () => {
        dialog.op = 'update'
      }
    },
    {
      label: `Copy sample${s}`,
      icon: 'pi pi-copy',
      command: async () => {
        const clipboard = JSON.stringify(
          app.data.sample.selected.map(({ sample_item_id, sample_batch_id, sample_item_name }) => ({
            sample_item_id,
            sample_batch_id,
            sample_item_name
          }))
        )
        try {
          await navigator.clipboard.writeText(clipboard)
        } catch (err) {
          console.warn(err)
        }
      }
    },
    {
      label: `Delete sample${s}`,
      icon: 'pi pi-trash',
      command: () => {
        confirm.require({
          icon: 'pi pi-exclamation-triangle',
          header: `Delete sample${s}`,
          message: `
            Are you sure you want to delete
            ${app.data.sample.selected.length} sample${s} from
            batch "${app.data.batch.focused.sample_batch_name}"?
          `,
          accept: async () => {
            // unload if necessary
            if (sample.context.sample_item_id == app.data.sample.focused?.sample_item_id) {
              app.data.sample.unfocus()
            }
            await app.data.sample.delete({
              sample_item_ids: app.data.sample.selectedIds
            })
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
    { separator: true, visible: !multiselecting },
    {
      label: `Recalibrate sample`,
      icon: 'pi pi-replay',
      command: () => {
        dialog.calibration = true
      },
      visible: !multiselecting
    },
    {
      label: `Rematch sample`,
      icon: 'pi pi-replay',
      command: async () => {
        await app.data.sample.rematch(sample.context)
      },
      visible: !multiselecting
    },
    {
      label: `Compute all peaks`,
      icon: 'pi pi-wave-pulse',
      command: async () => {
        await app.data.peak.computeAll(sample.context)
      },
      visible: !multiselecting
    }
  ]
})
</script>

<template>
  <div
    v-if="!app.data.sample.loading"
    style="min-height: 2rem"
    v-help.right_start="
      `<h1>Samples</h1>
    
      <p>Sample items. Right click to perform actions.</p>`
    "
  >
    <DataTable
      v-if="samples.length > 0 && app.data.batch.focused"
      :value="samples"
      dataKey="sample_item_id"
      selectionMode="multiple"
      :metaKeySelection="true"
      v-model:selection="app.data.sample.selected"
      v-model:contextMenuSelection="sample.context"
      contextMenu
      @rowContextmenu="onContextMenuClick"
      reorderableColumns
      :sortField="config.sortField"
      :sortOrder="config.sortOrder"
      @sort="
        ({ sortField, sortOrder }) => {
          config.sortField = sortField
          config.sortOrder = sortOrder
        }
      "
      @column-reorder="
        ({ dragIndex, dropIndex }) => {
          let columns = clone(config.columns)
          const column = columns.splice(dragIndex - 1, 1)[0]
          columns.splice(dropIndex - 1, 0, column)
          config.columns = columns
        }
      "
      size="small"
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

      <template v-for="{ field, label, kind } in config.columns" :key="field">
        <Column v-if="kind == 'standard'" :field="field" :header="label" sortable>
          <template #body="{ data }">
            <span class="field">
              <BaseCopyableField :field="data[field]" />
            </span>
          </template>
        </Column>
        <Column v-if="kind == 'custom'" field="sample_item_attributes" :header="label" sortable>
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
  <!-- modals etc. -->
  <ContextMenu ref="contextMenuRef" :model="contextMenuEntries" />
  <DialogSampleOp v-model:action="dialog.op" :item="sample.context" />
  <DialogCalibration v-model:visible="dialog.calibration" :context="sample.context" />
</template>
