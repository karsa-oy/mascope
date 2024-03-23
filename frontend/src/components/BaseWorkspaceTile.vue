<script setup>
import { useModalStore } from '@/stores/modal'
import { useTargetsStore } from '@/stores/targets'
import { useWorkspaceStore } from '@/stores/workspace'

const modalStore = useModalStore()
const targetsStore = useTargetsStore()
const workspaceStore = useWorkspaceStore()

const props = defineProps({
  workspace: {
    required: true
  }
})

function onClick() {
  workspaceStore.load(props.workspace.workspace_id)
  targetsStore.load()
}
</script>

<template>
  <div class="base-tile">
    <header class="tile-card-header">
      <p class="tile-card-header-title" @click="onClick">
        {{ workspace.workspace_name }}
      </p>
      <b-dropdown aria-role="list">
        <template #trigger>
          <b-icon icon="dots-horizontal" size="small" role="button"></b-icon>
        </template>
        <b-dropdown-item
          aria-role="listitem"
          @click="
            () => {
              modalStore.state.workspaceSaveProps = {
                action: 'edit',
                workspace_id: workspace.workspace_id
              }
              modalStore.activate({
                modal: 'workspaceSave'
              })
            }
          "
        >
          Edit
        </b-dropdown-item>
        <b-dropdown-item
          aria-role="listitem"
          @click="
            () => {
              modalStore.state.workspaceSaveProps = {
                action: 'delete',
                workspace_id: workspace.workspace_id
              }
              modalStore.activate({
                modal: 'workspaceSave'
              })
            }
          "
        >
          Delete
        </b-dropdown-item>
      </b-dropdown>
    </header>
    <div class="tile-card-content">
      {{ workspace.workspace_description }}
    </div>
  </div>
</template>
