<script setup>
import { ref, onMounted, watch } from 'vue'

import ContextMenu from 'primevue/contextmenu'
import { useConfirm } from 'primevue/useconfirm'

import { DialogTargetCompoundUpdate } from '@/lib/dialogs'

import { useApp } from '@/stores'
import { useIonContextMenu } from './stores'

const app = useApp()
const confirm = useConfirm()
const contextMenu = useIonContextMenu()

const contextMenuRef = ref()
onMounted(() => {
  contextMenu.ref = contextMenuRef.value
})

// Watch for removeCompound dialog trigger
watch(
  () => contextMenu.dialog.removeCompound,
  (shouldRemove) => {
    if (!shouldRemove || !contextMenu.selection) return

    const ionRecord = contextMenu.selection
    const collection = app.data.target.collection.detailed
    if (!collection) return

    const batchCount = collection?.sample_batches_count ?? 0

    confirm.require({
      icon: 'pi pi-exclamation-triangle',
      header: `Remove target compound '${contextMenu.compoundLabel}'`,
      message: `Are you sure you want to remove compound '${contextMenu.compoundLabel}' from target collection 
      '${collection.target_collection_name}' used in ${batchCount} batches? This will require rematching the affected batches.`,
      accept: () => {
        const remainingCompoundIds = [
          ...new Set(
            app.data.match.ion.list
              .filter((ion) => ion.target_compound_id !== ionRecord.target_compound_id)
              .map((ion) => ion.target_compound_id)
          )
        ]
        app.data.target.collection.update({
          target_collection_id: collection.target_collection_id,
          target_collection_name: collection.target_collection_name,
          target_collection_type: collection.target_collection_type,
          target_compound_ids: remainingCompoundIds
        })
      },
      acceptProps: { icon: 'pi pi-minus', label: 'Remove' },
      rejectProps: { label: 'Cancel', severity: 'secondary' }
    })

    // Reset the dialog trigger
    contextMenu.dialog.removeCompound = false
  }
)
</script>

<template>
  <ContextMenu ref="contextMenuRef" :model="contextMenu.entries" />
  <DialogTargetCompoundUpdate
    v-model:visible="contextMenu.dialog.editCompound"
    :compound="contextMenu.selection"
  />
</template>
