<script setup>
import { computed } from 'vue'

import ThePaneBrowserSample from './ThePaneBrowserSample.vue'
import ThePaneBrowserTarget from './ThePaneBrowserTarget.vue'

import { useWorkspaceStore, useSampleStore } from '@/stores'

const workspaceStore = useWorkspaceStore()
const sampleStore = useSampleStore()

const workspaceHomeText = computed(() => {
  if (workspaceStore.active) {
    return `${workspaceStore.active.workspace_name}`
  } else {
    return `Loading workspace...`
  }
})
</script>

<template>
  <section>
    <section style="padding: 2em 2em 2em 2em">
      <h1 class="title is-4">{{ workspaceHomeText }}</h1>
    </section>
    <the-pane-browser-sample></the-pane-browser-sample>
    <div v-if="!sampleStore.active || sampleStore.matched">
      <!-- hide target browser if selected sample is not matched -->
      <the-pane-browser-target></the-pane-browser-target>
    </div>
  </section>
</template>
