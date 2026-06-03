<script setup>
import { ref, computed, onMounted } from 'vue'

import ContextMenu from 'primevue/contextmenu'

import { DialogBatchOp, DialogTargetCollectionOp } from '@/lib/dialogs'

import { useCollectionContextMenu } from './stores'

const contextMenu = useCollectionContextMenu()

const contextMenuRef = ref()
onMounted(() => {
  contextMenu.ref = contextMenuRef.value
})

const collectionOp = computed({
  get: () => (contextMenu.dialog.op === 'update_targets' ? null : contextMenu.dialog.op),
  set: (v) => {
    contextMenu.dialog.op = v
  }
})
</script>

<template>
  <ContextMenu ref="contextMenuRef" :model="contextMenu.entries" @hide="contextMenu.clear" />
  <DialogTargetCollectionOp v-model:action="collectionOp" />
  <DialogBatchOp
    v-model:action="contextMenu.dialog.op"
    :visible="contextMenu.dialog.op === 'update_targets'"
  />
</template>
