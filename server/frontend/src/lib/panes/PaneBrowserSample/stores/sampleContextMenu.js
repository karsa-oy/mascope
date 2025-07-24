import { ref, reactive, computed, watch } from 'vue'
import { defineStore } from 'pinia'

import { useConfirm } from 'primevue/useconfirm'

import { api } from '@/api'
import { useApp } from '@/stores'

import { useBatchContextMenu } from './batchContextMenu.js'
import { useCustomizerPopover } from './customizerPopover.js'
import { useClipboard } from './clipboard.js'

export const useSampleContextMenu = defineStore('browser.sample.sampleCtxMenu', () => {
  const app = useApp()
  const confirm = useConfirm()

  // local deps
  const batchContextMenu = useBatchContextMenu()
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

  // paste context
  const pasteBatchId = computed(() => row.value?.sample_batch_id ?? app.data.batch.focusedId)
  const pasteValid = computed(
    () =>
      pasteBatchId.value &&
      (clipboard.op === 'copy' ||
        (clipboard.op === 'cut' &&
          clipboard.samples.every(({ sample_batch_id }) => sample_batch_id !== pasteBatchId.value)))
  )
  const sampleContext = computed(() => row.value || app.data.sample.selected.length > 0)

  // actions
  async function onClick(event) {
    await clipboard.read()
    row.value = event?.data ?? null
    if (!app.data.sample.isSelected(row.value)) {
      app.data.sample.focus(row.value)
    }
    if (pasteValid.value || sampleContext.value) {
      show(event)
    }
  }
  function show(event) {
    batchContextMenu.hide()
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
        visible: clipboard.samples !== null && pasteValid.value,
        command: async () => {
          if (clipboard.samples.length > 0) {
            if (clipboard.op === 'copy') {
              await app.data.sample.copy({
                sample_item_ids: clipboard.samples.map((s) => s.sample_item_id),
                sample_batch_id: pasteBatchId.value
              })
            } else if (clipboard.op === 'cut') {
              await app.data.sample.move({
                sample_item_ids: clipboard.samples.map((s) => s.sample_item_id),
                sample_batch_id: pasteBatchId.value
              })
              clipboard.clear()
            }
          }
        }
      },
      {
        separator: true,
        visible: clipboard.samples !== null && pasteValid.value && sampleContext.value
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
        visible: sampleContext.value,
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
        visible: sampleContext.value,
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
        visible: sampleContext.value,
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
      { separator: true, visible: sampleContext.value },
      {
        label: `Download`,
        icon: 'pi pi-file-export',
        visible: sampleContext.value,
        items: [
          {
            label: `Sample file${s}`,
            icon: 'pi ph ph-test-tube',
            command: () => {
              api.http.post(
                `/file/download`,
                {
                  sample_file_ids: app.data.sample.selected.map(
                    ({ sample_file_id }) => sample_file_id
                  )
                },
                {
                  use: 'process',
                  type: 'download_sample_files'
                }
              )
            }
          },
          {
            label: 'Peak data',
            icon: 'pi pi-wave-pulse',
            command: async () => {
              await app.data.sample.exportPeaks(row.value)
            },
            visible: !multiselecting
          }
        ]
      },
      {
        label: 'Process',
        icon: 'pi ph ph-hourglass-medium',
        visible: !multiselecting && sampleContext.value,
        items: [
          {
            label: `Recalibrate`,
            icon: 'pi ph ph-scales',
            command: () => {
              dialog.calibration = true
            },
            visible: !multiselecting
          },
          {
            label: `Rematch`,
            icon: 'pi ph ph-binoculars',
            command: async () => {
              await app.data.sample.rematch(row.value)
            },
            visible: !multiselecting
          },
          {
            label: `Detect peaks`,
            icon: 'pi pi-wave-pulse',
            command: async () => {
              await app.data.peak.computeAll(row.value)
            },
            visible: !multiselecting
          }
        ]
      }
    ]
  })

  return {
    ref: menu,
    onClick,
    row,
    show,
    hide,
    selection,
    clear,
    entries,
    dialog
  }
})
