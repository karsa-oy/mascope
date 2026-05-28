import { ref, reactive, computed } from 'vue'
import { defineStore } from 'pinia'

import { useApp } from '@/stores'

import { useClipboard } from './clipboard.js'

export const useDatasetContextMenu = defineStore('browser.sample.datasetCtxMenu', () => {
  const app = useApp()

  // local deps
  const clipboard = useClipboard()

  // state
  const menu = ref()
  const row = ref(null)
  const selection = ref(null)
  const dialog = reactive({
    op: null
  })

  // paste is valid for a cut dataset originating from a different workspace
  const pasteValid = computed(
    () =>
      clipboard.op === 'cut' &&
      clipboard.dataset !== null &&
      clipboard.dataset.workspace_id !== app.data.workspace.focusedId
  )

  // actions
  async function onClick(event) {
    await clipboard.read()
    row.value = event?.data ?? null
    // show on a row (cut/edit/delete) or when a paste is available (empty space)
    if (row.value || pasteValid.value) {
      show(event)
    } else {
      hide()
    }
  }
  function show(event) {
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
      label: 'Paste dataset',
      icon: 'pi pi-clipboard',
      visible: pasteValid.value,
      command: async () => {
        await app.data.dataset.move({
          dataset_id: clipboard.dataset.dataset_id,
          source_workspace_id: clipboard.dataset.workspace_id,
          target_workspace_id: app.data.workspace.focusedId
        })
        clipboard.clear()
      }
    },
    {
      separator: true,
      visible: pasteValid.value && row.value !== null
    },
    {
      label: 'Cut dataset',
      icon: 'pi ph ph-scissors',
      // ACQUISITION datasets are auto-managed - never movable
      visible: row.value !== null && row.value?.dataset_type !== 'ACQUISITION',
      command: () => {
        clipboard.cut({
          dataset_id: row.value.dataset_id,
          workspace_id: row.value.workspace_id,
          dataset_name: row.value.dataset_name
        })
      }
    },
    {
      label: 'Edit dataset',
      icon: 'pi pi-pen-to-square',
      visible: row.value !== null,
      command: () => {
        dialog.op = 'edit'
      }
    },
    {
      label: 'Delete dataset',
      icon: 'pi pi-trash',
      visible: row.value !== null,
      command: () => {
        dialog.op = 'delete'
      }
    }
  ])

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
