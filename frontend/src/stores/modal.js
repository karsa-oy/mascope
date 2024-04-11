import { reactive } from 'vue'
import { defineStore } from 'pinia'

export const useModalStore = defineStore('modal', () => {
  const state = reactive({
    // active modal indicator
    active: null,
    // modal-specific active sync helpers and data
    targetCollectionOpActive: false,
    targetCollectionOpProps: {},
    workspaceSaveActive: false,
    workspaceSaveProps: {
      // action ('create', 'edit' or 'delete')
      // workspaceId (required for edit or delete)
    },
    sampleBatchImportActive: false,
    sampleBatchImportProps: {},
    sampleBatchOpActive: false,
    sampleBatchOpProps: {
      // action ('create', 'edit' or 'delete')
      // workspaceId (required for edit or delete)
    },
    sampleFileAttributesSaveActive: false,
    sampleFileAttributesSaveProps: {
      // action ('create', 'edit' or 'delete')
      // sampleFileId (required for edit or delete)
    },
    sampleItemAttributesSaveActive: false,
    sampleItemAttributesSaveProps: {
      // action ('create', 'edit' or 'delete')
      // sampleItemId (required for edit or delete)
    },
    sampleItemOverviewActive: false,
    sampleItemOverviewProps: {},
    sampleItemTargetIonActive: false
  })

  function activate({ modal }) {
    deactivate()
    state.active = modal
    state[modal + 'Active'] = true
  }
  function deactivate() {
    Object.keys(state)
      .filter((prop) => prop.endsWith('Active'))
      .filter((prop) => state[prop])
      .forEach((prop) => {
        state[prop] = false
      })
    state.active = null
  }

  return { state, activate, deactivate }
})
