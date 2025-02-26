import { ref, reactive, computed } from 'vue'
import { defineStore } from 'pinia'

import { useConfirm } from 'primevue/useconfirm'

import { useApp } from '@/stores'
import { useBatchDeleteDialog } from '@/lib/dialogs'
import { generateCopyName } from '@/api/utils'

import { useSampleContext } from './sampleContext.js'
import { useCustomizerPopover } from './customizerPopover.js'
import { useClipboard } from './clipboard.js'

export const useBatchContext = defineStore('browser.batch.context', () => {
  const app = useApp()
  const confirm = useConfirm()

  // local deps
  const sampleContext = useSampleContext()
  const customizerPopover = useCustomizerPopover()
  const clipboard = useClipboard()

  // state
  const menu = ref()
  const row = ref()
  const selection = ref()
  const dialog = reactive({
    op: null,
    delete: useBatchDeleteDialog(),
    calibration: false
  })

  // actions
  async function onClick(event) {
    await clipboard.read()
    row.value = event?.data ?? null
    if (row.value || clipboard.batch !== null) {
      show(event)
    } else {
      hide()
    }
  }
  function show(event) {
    sampleContext.hide()
    customizerPopover.hide()
    menu.value?.show(event?.originalEvent ?? event)
  }
  function hide() {
    menu.value?.hide()
    row.value = null
  }
  function clear() {
    selection.value = null
  }

  // context menu entries
  const entries = computed(() => [
    {
      label: 'Paste batch',
      icon: 'pi pi-clipboard',
      command: async () => {
        if (clipboard.batch) {
          if (clipboard.op === 'copy') {
            await app.data.batch.copy({
              sample_batch_id: clipboard.batch.sample_batch_id,
              workspace_id: app.data.workspace.focusedId,
              sample_batch_name: generateCopyName(clipboard.batch.sample_batch_name),
              sample_batch_description: clipboard.batch.sample_batch_description
            })
          }
        }
      },
      visible: clipboard.batch !== null
    },
    {
      label: `Paste sample${clipboard.samples?.length > 1 ? 's' : ''}`,
      icon: 'pi pi-clipboard',
      visible: clipboard.samples !== null,
      command: async () => {
        if (clipboard.samples.length > 0) {
          if (clipboard.op === 'copy') {
            await app.data.sample.copy({
              sample_item_ids: clipboard.samples.map((s) => s.sample_item_id),
              sample_batch_id: row.value.sample_batch_id
            })
          } else if (clipboard.op === 'cut') {
            await app.data.sample.move({
              sample_item_ids: clipboard.samples.map((s) => s.sample_item_id),
              sample_batch_id: row.value.sample_batch_id
            })
          }
        }
      }
    },
    {
      separator: true,
      visible: (clipboard.batch !== null || clipboard.samples !== null) && row.value !== null
    },
    {
      label: 'Edit batch',
      icon: 'pi pi-pen-to-square',
      command: () => {
        dialog.op = 'update'
      },
      visible: row.value !== null
    },
    {
      label: 'Edit batch targets',
      icon: 'pi pi-bullseye',
      command: () => {
        dialog.op = 'update_targets'
      },
      visible: row.value !== null
    },
    {
      label: 'Copy batch',
      icon: 'pi pi-copy',
      command: () => {
        clipboard.copy(row.value)
      },
      visible: row.value !== null
    },
    {
      label: 'Delete batch',
      icon: 'pi pi-trash',
      command: () => dialog.delete(row.value),

      visible: row.value !== null
    },
    { separator: true, visible: row.value !== null },
    {
      label: 'Export batch',

      icon: 'pi pi-file-export',
      command: async () => {
        await app.data.batch.exportCsv(row.value)
      },
      visible: row.value !== null
    },
    {
      label: 'Export peaks',
      icon: 'pi pi-file-export',
      command: () => {
        confirm.require({
          icon: 'pi pi-info-circle',
          header: 'Export batch peak data',
          message: `Export peak data for batch "${row.value.sample_batch_name}"?`,
          accept: () => {
            app.data.batch.exportPeaks(row.value)
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
      visible: row.value !== null
    },
    {
      separator: true,

      visible: row.value !== null
    },
    {
      label: `Recalibrate batch`,
      icon: 'pi pi-replay',
      command: () => {
        dialog.calibration = true
      },
      visible: row.value !== null
    },
    {
      label: 'Rematch batch',
      icon: 'pi pi-replay',
      command: () => app.data.batch.rematch(row.value),
      visible: row.value !== null
    }
  ])

  return {
    onClick,
    row,
    show,
    hide,
    selection,
    clear,
    menu,
    entries,
    dialog
  }
})
