<script setup>
import { ref, computed } from 'vue'

import table from '@/lib/table'

import { useAppStore, useModalStore, useWorkspaceStore } from '@/stores'

const appStore = useAppStore()
const modalStore = useModalStore()
const workspaceStore = useWorkspaceStore()

const workspaceName = ref(null)
const workspaceDesc = ref(null)

const action = computed(() => {
  return modalStore.state.workspaceSaveProps.action
})
const oldWorkspace = computed(() => {
  if (actionIs('edit', 'delete')) {
    return table.get(appStore.workspaces, {
      workspace_id: modalStore.state.workspaceSaveProps.workspace_id
    })
  } else {
    return null
  }
})
const modalTitle = computed(() => {
  let title
  const workspaceName = oldWorkspace.value ? oldWorkspace.value.workspace_name : ''
  switch (action.value) {
    case 'create':
      title = `Create a new workspace`
      break
    case 'edit':
      title = `Edit workspace ${workspaceName}`
      break
    case 'delete':
      title = `Delete workspace ${workspaceName}`
      break
  }
  return title
})

function actionIs(...actions) {
  return actions.includes(action.value)
}
function loadWorkspace() {
  workspaceName.value = oldWorkspace.value ? oldWorkspace.value.workspace_name : null
  workspaceDesc.value = oldWorkspace.value ? oldWorkspace.value.workspace_description : null
}
</script>

<template>
  <section>
    <b-modal
      v-model="modalStore.state.workspaceSaveActive"
      has-modal-card
      trap-focus
      :can-cancel="true"
      aria-role="dialog"
      aria-modal
      @after-enter="loadWorkspace"
      @close="modalStore.deactivate"
      :type="actionIs('delete') ? 'is-danger' : 'is-primary'"
    >
      <div class="modal-card" style="width: 500px">
        <header class="modal-card-head">
          <h2 class="subtitle">{{ modalTitle }}</h2>
        </header>
        <section class="modal-card-body" style="min-height: 250px">
          <b-field v-if="actionIs('create', 'edit')" label="Name">
            <b-input v-model="workspaceName"></b-input>
          </b-field>
          <b-field v-if="actionIs('create', 'edit')" label="Description">
            <b-input v-model="workspaceDesc"></b-input>
          </b-field>
          <p v-if="actionIs('delete')">Are you sure you want to delete this workspace?</p>
        </section>
        <footer class="modal-card-foot">
          <b-button type="is-warning" icon-left="close" expanded @click="modalStore.deactivate">
            Cancel
          </b-button>

          <b-button
            v-if="actionIs('edit')"
            type="is-primary"
            icon-left="content-save"
            expanded
            @click="
              () => {
                workspaceStore.updateWorkspace({
                  workspace_id: oldWorkspace.workspace_id,
                  workspace_name: workspaceName,
                  workspace_description: workspaceDesc
                })
                modalStore.deactivate()
              }
            "
          >
            Save
          </b-button>
          <b-button
            v-if="actionIs('create')"
            type="is-primary"
            icon-left="content-save"
            expanded
            @click="
              () => {
                workspaceStore.createWorkspace({
                  workspace_name: workspaceName,
                  workspace_description: workspaceDesc
                })
                modalStore.deactivate()
              }
            "
          >
            Create
          </b-button>
          <b-button
            v-if="actionIs('delete')"
            type="is-danger"
            icon-left="delete"
            expanded
            @click="
              () => {
                workspaceStore.deleteWorkspace(oldWorkspace)
                modalStore.deactivate()
              }
            "
          >
            Delete
          </b-button>
        </footer>
      </div>
    </b-modal>
  </section>
</template>
