import { ref, reactive, computed } from 'vue'
import { defineStore } from 'pinia'
import { useApp } from '@/stores'

export const useIonContextMenu = defineStore('ionContextMenu', () => {
  const app = useApp()

  const ref_ = ref(null)
  const selection = ref(null)
  const dialog = reactive({
    editCompound: false,
    removeCompound: false
  })

  const compoundLabel = computed(
    () =>
      selection.value?.target_compound_name ||
      selection.value?.target_compound_formula ||
      'Unknown Compound'
  )

  const entries = computed(() => {
    if (!selection.value) return []

    const collection = app.data.target.collection.detailed

    return [
      {
        label: `Edit compound '${compoundLabel.value}'`,
        icon: 'pi pi-pen-to-square',
        command: () => {
          dialog.editCompound = true
        }
      },
      {
        label: `Remove '${compoundLabel.value}' from '${collection?.target_collection_name || 'collection'}'`,
        icon: 'pi pi-minus',
        command: () => {
          dialog.removeCompound = true
        },
        disabled: !collection
      }
    ]
  })

  const onClick = async (event) => {
    selection.value = event.data
    ref_.value?.toggle(event.originalEvent)
  }

  const clear = () => {
    selection.value = null
  }

  return {
    ref: ref_,
    selection,
    dialog,
    entries,
    compoundLabel,
    onClick,
    clear
  }
})
