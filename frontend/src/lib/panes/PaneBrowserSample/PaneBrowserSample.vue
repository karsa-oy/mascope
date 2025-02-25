<script setup>
import { ref, reactive, computed, watch } from 'vue'

import Panel from 'primevue/panel'
import Button from 'primevue/button'
import TabMenu from 'primevue/tabmenu'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import ContextMenu from 'primevue/contextmenu'
import { useConfirm } from 'primevue/useconfirm'

import { generateCopyName } from '@/api'
import { BaseCopyableField } from '@/lib/base'
import { DialogBatchOp, DialogCalibration, useBatchDeleteDialog } from '@/lib/dialogs'
import { batchExportCsv } from '@/lib/table'
import { useApp } from '@/stores'

import SampleTable from './SampleTable.vue'
import SampleTableCustomizer from './SampleTableCustomizer.vue'

const confirm = useConfirm()

const app = useApp()

const dialog = reactive({
  op: null,
  delete: useBatchDeleteDialog(),
  calibration: false
})

const batch = reactive({
  expanded: {},
  context: null,
  pasted: null
})

const pending = reactive({
  batchExport: false,
  peakExport: false
})

watch(
  () => app.data.batch.focused,
  async (focused) => {
    if (focused) {
      batch.expanded = { [focused.sample_batch_id]: true }
      // handle pending operations
      if (pending.batchExport) {
        await batchExportCsv()
        pending.batchExport = false
      }
      if (pending.peakExport) {
        await app.data.batch.exportPeaks(app.data.batch.focused)
        pending.peakExport = false
      }
    } else {
      batch.expanded = {}
    }
  }
)

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

// component refs
const contextMenuRef = ref()
// other refs
const sampleContextMenuRef = ref()
const tableCustomizerPopoverRef = ref()

// prevent default event handling
const onContextMenuClick = (event) => {
  if (app.data.batch.focusedId == batch.context?.sample_batch_id) {
    sampleContextMenuRef.value?.hide()
    tableCustomizerPopoverRef.value?.hide()
    contextMenuRef.value.show(event.originalEvent)
  } else {
    contextMenuRef.value.hide()
  }
}

const contextMenuEntries = computed(() => [
  {
    label: 'Paste batch',
    icon: 'pi pi-clipboard',
    command: async () => {
      if (batch.pasted) {
        await app.data.batch.copy({
          sample_batch_id: batch.pasted.sample_batch_id,
          workspace_id: app.data.workspace.focusedId,
          sample_batch_name: generateCopyName(batch.pasted.sample_batch_name),
          sample_batch_description: batch.pasted.sample_batch_description
        })
      }
    },
    visible: batch.pasted !== null
  },
  {
    separator: true,
    visible: batch.pasted !== null && batch.context !== null
  },
  {
    label: 'Edit batch',
    icon: 'pi pi-pen-to-square',
    command: () => {
      dialog.op = 'update'
    },
    visible: batch.context !== null
  },
  {
    label: 'Edit batch targets',
    icon: 'pi pi-bullseye',
    command: () => {
      dialog.op = 'update_targets'
    },
    visible: batch.context !== null
  },
  {
    label: 'Copy batch',
    icon: 'pi pi-copy',
    command: async () => {
      const clipboard = JSON.stringify(batch.context)
      try {
        await navigator.clipboard.writeText(clipboard)
      } catch (err) {
        console.warn(err)
      }
    },
    visible: batch.context !== null
  },
  {
    label: 'Delete batch',
    icon: 'pi pi-trash',
    command: () => dialog.delete(batch.context),
    visible: batch.context !== null
  },
  { separator: true, visible: batch.context !== null },
  {
    label: 'Export batch',

    icon: 'pi pi-file-export',
    command: async () => {
      if (app.data.batch.focused?.sample_batch_id == batch.context.sample_batch_id) {
        await app.data.batch.exportCsv(app.data.batch.focused)
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
      dialog.calibration = true
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
// copy-paste

async function parseClipboard() {
  let clipboard, pasted
  try {
    clipboard = await navigator.clipboard.readText()
    pasted = JSON.parse(clipboard)
  } catch (err) {
    return
  }
  if (pasted?.sample_batch_id && !pasted?.sample_item_id) {
    batch.pasted = pasted
  }
}

const config = ref({})
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
          contextMenuRef.show(event)
        }
      }
    "
    :pt="
      app.ui.help.right(`
        <h1>Sample Browser</h1>

        <p>Shows the samples in your workspace,
        providing features to organize them into
        batches.</p>

        <p>Right click batches and samples to
        perform actions.</p>
      `)
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
            dialog.op = 'create'
          }
        "
      />
    </template>
    <div class="scroller">
      <DataTable
        :value="tree"
        dataKey="sample_batch_id"
        selectionMode="single"
        :metaKeySelection="false"
        v-model:selection="app.data.batch.focused"
        v-model:expandedRows="batch.expanded"
        v-model:contextMenuSelection="batch.context"
        contextMenu
        @rowContextmenu="
          (e) => {
            onContextMenuClick(e)
            parseClipboard()
          }
        "
        sortField="sample_batch_utc_created"
        :sortOrder="-1"
        size="small"
      >
        <!-- batch columns -->
        <Column header="Batch" field="sample_batch_name" sortable>
          <template #body="{ data }">
            <div
              class="row"
              style="justify-content: flex-start"
              v-help.right="
                `<h1>Batch</h1>

                <p>A group of samples. Right click to perform actions.</p>`
              "
            >
              <span
                :class="`pi pi-chevron-${data.sample_batch_id in batch.expanded ? 'down' : 'right'}`"
                style="font-size: smaller; margin-right: 0.5rem"
              />
              <BaseCopyableField
                :field="data.sample_batch_name"
                v-tooltip="{ value: `${data.sample_batch_description}`, showDelay: 1000 }"
              />
            </div>
          </template>
        </Column>
        <Column>
          <template #body="{ data }">
            <SampleTableCustomizer
              v-if="data.sample_batch_id in batch.expanded"
              v-model:config="config"
              @popover="
                (ref) => {
                  contextMenuRef.hide() // hide batch context menu
                  sampleContextMenuRef?.hide() // hide sample context menu (if open)
                  tableCustomizerPopoverRef = ref // save customizer popover ref
                }
              "
            />
          </template>
        </Column>
        <!-- sample table expansion -->
        <template #expansion="{ data }">
          <SampleTable
            :batch="data"
            v-model:config="config"
            @contextMenu="
              (ref) => {
                contextMenuRef.hide() // hide batch context menu
                tableCustomizerPopoverRef?.hide() // hide customizer popover
                sampleContextMenuRef = ref // save sample context menu ref
              }
            "
          />
        </template>
      </DataTable>
    </div>
  </Panel>
  <!-- modals etc -->
  <ContextMenu ref="contextMenuRef" :model="contextMenuEntries" />
  <DialogBatchOp v-model:action="dialog.op" :batch="batch.context" />
  <DialogCalibration v-model:visible="dialog.calibration" :context="batch.context" />
</template>
