import { ref, reactive, computed } from 'vue'
import { defineStore } from 'pinia'

import { useConfirm } from 'primevue/useconfirm'

import { useApp } from '@/stores'

import { useBatchContext } from './batchContext.js'
import { useCustomizerPopover } from './customizerPopover.js'
import { useClipboard } from './clipboard.js'

export const useSampleContext = defineStore('browser.sample.context', () => {
  const app = useApp()
  const confirm = useConfirm()

  // local deps
  const batchContext = useBatchContext()
  const customizerPopover = useCustomizerPopover()
  const clipboard = useClipboard()

  // state
  const menu = ref()
  const row = ref(null)
  const selection = ref(null)
  const dialog = reactive({
    op: null,
    calibration: false,
    instrumentConfig: false
  })

  // actions
  async function onClick(event) {
    await clipboard.read()
    row.value = event?.data ?? null
    if (!app.data.sample.isSelected(row.value)) {
      app.data.sample.focus(row.value)
    }
    show(event)
  }
  function show(event) {
    batchContext.hide()
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
  const entries = computed(() => {
    const multiselecting = app.data.sample.selected.length > 1
    const s = multiselecting ? 's' : ''
    return [
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
        visible: clipboard.samples !== null
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
          clipboard.copy(
            app.data.sample.selected.map(
              ({ sample_item_id, sample_batch_id, sample_item_name }) => ({
                sample_item_id,
                sample_batch_id,
                sample_item_name
              })
            )
          )
        }
      },
      {
        label: `Cut sample${s}`,
        icon: 'pi ph ph-scissors',
        command: async () => {
          clipboard.cut(
            app.data.sample.selected.map(
              ({ sample_item_id, sample_batch_id, sample_item_name }) => ({
                sample_item_id,
                sample_batch_id,
                sample_item_name
              })
            )
          )
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
              const sample_item_ids = app.data.sample.selectedIds
              app.data.sample.unfocus()
              await app.data.sample.delete({
                sample_item_ids
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
          await app.data.sample.rematch(row.value)
        },
        visible: !multiselecting
      },
      {
        label: `Compute all peaks`,
        icon: 'pi pi-wave-pulse',
        command: async () => {
          await app.data.peak.computeAll(row.value)
        },
        visible: !multiselecting
      }
    ]
  })

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
