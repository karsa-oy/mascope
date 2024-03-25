<script setup>
import BaseWorkspaceTile from '@/components/base/BaseWorkspaceTile.vue'
import ThePaneBrowser from '@/components/panes/ThePaneBrowser.vue'

import { useAppStore, useModalStore, useWorkspaceStore } from '@/stores'

const appStore = useAppStore()
const modalStore = useModalStore()
const workspaceStore = useWorkspaceStore()
</script>

<template>
  <template v-if="!workspaceStore.active">
    <h1 class="title is-5">Workspaces</h1>
    <section class="base-tile-container">
      <base-workspace-tile
        v-for="workspace in appStore.workspaces"
        :key="workspace.id"
        :workspace="workspace"
      ></base-workspace-tile>
    </section>
    <section style="padding: 0.5em">
      <b-button
        type="is-primary"
        style="position: fixed; right: 5em; bottom: 2em"
        @click="
          () => {
            modalStore.state.workspaceSaveProps = {
              action: 'create'
            }
            modalStore.activate({
              modal: 'workspaceSave'
            })
          }
        "
      >
        Create workspace
      </b-button>
    </section>
  </template>
  <template v-else>
    <the-pane-browser />
  </template>
</template>
