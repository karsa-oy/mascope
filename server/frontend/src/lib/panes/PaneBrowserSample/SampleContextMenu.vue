<script setup>
import { ref, onMounted } from 'vue'

import ContextMenu from 'primevue/contextmenu'

import { useApp } from '@/stores'

import { useSampleContextMenu } from './stores'

const app = useApp()

const contextMenu = useSampleContextMenu()

const contextMenuRef = ref()
onMounted(() => {
  contextMenu.ref = contextMenuRef.value
})
</script>

<template>
  <ContextMenu ref="contextMenuRef" :model="contextMenu.entries" @hide="contextMenu.clear" />
</template>
