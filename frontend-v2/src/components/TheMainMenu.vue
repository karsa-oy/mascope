<script setup>
  import { computed } from 'vue'

  import BaseMenuBar from './BaseMenuBar.vue'

  import { useInstrumentStore } from '@/stores/instrument'
  import { useBatchStore } from '@/stores/batch'
  import { useWorkspaceStore } from '@/stores/workspace'

  const instrumentStore = useInstrumentStore()
  const batchStore = useBatchStore()
  const workspaceStore = useWorkspaceStore()

  const allButtonsDisabled = computed(
    () => instrumentStore.scenthoundModeActive && instrumentStore.acquisitionActive
      ? true
      : false
  )

  const buttons = computed(() => [
    {
      disabled: allButtonsDisabled.value,
      icon: 'home',
      label: 'Workspace home',
      path: '/',
      visible: true,
    },
    {
      disabled: allButtonsDisabled.value || !(batchStore.active && instrumentStore.active),
      icon: 'dog-side',
      label: 'Scenthound',
      path: '/scenthound',
      visible: true,
    },
    {
      disabled: allButtonsDisabled.value,
      icon: 'chart-scatter-plot',
      label: 'Batch overview',
      path: '/batch-overview',
      visible: batchStore.active,
    },
  ].filter((b) => b.visible))

  const footerButtons = computed(() => [
    {
      disabled: allButtonsDisabled.value,
      icon: 'logout-variant',
      label: 'Change workspace',
      path: '/',
      onClick: workspaceStore.unload,
      visible: true,
    },
  ].filter((b) => b.visible)
  )
</script>

<template>
  <base-menu-bar :buttons="buttons" :footerButtons="footerButtons"> </base-menu-bar>
</template>