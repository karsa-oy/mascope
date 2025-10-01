import { ref, reactive, computed } from 'vue'
import { defineStore } from 'pinia'
import { useApp } from '@/stores'

export const useCollectionContextMenu = defineStore('collectionContextMenu', () => {
  const app = useApp()

  const ref_ = ref(null)
  const selection = ref(null)
  const dialog = reactive({
    op: null
  })

  const entries = computed(() => {
    if (!selection.value) return []

    return [
      {
        label: `Edit '${selection.value.target_collection_name}'`,
        icon: 'pi pi-pen-to-square',
        command: () => {
          dialog.op = 'update'
        }
      },
      {
        label: 'Edit batches',
        icon: 'pi pi-pen-to-square',
        command: () => {
          dialog.op = 'update_batches'
        }
      },
      {
        label: `Delete '${selection.value.target_collection_name}'`,
        icon: 'pi pi-trash',
        command: () => {
          dialog.op = 'delete'
        }
      }
    ]
  })

  const onClick = async (event) => {
    // Handle DataTable row context menu events
    const data = event?.data || selection.value
    if (!data?.target_collection_id) return

    selection.value = data
    // Load detailed data for context menu operations
    await app.data.target.collection.loadDetailed(data.target_collection_id)
    ref_.value?.toggle(event.originalEvent || event)
  }

  const clear = () => {
    selection.value = null
  }

  return {
    ref: ref_,
    selection,
    dialog,
    entries,
    onClick,
    clear
  }
})
