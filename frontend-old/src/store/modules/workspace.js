import { make } from 'vuex-pathify'
import { handleApiRequest, getApiData } from './apiHelper'

const state = {
  active: null,
  batches: [],
}

export default {
  namespaced: true,
  state,
  mutations: make.mutations(state),
  actions: {
    // data loading
    async load({ dispatch, commit, rootState }, workspaceId) {
      if (state.active) await dispatch('unload', false)
      rootState.api.emit('subscribe', workspaceId)
      await dispatch('loadWorkspace', workspaceId)
      await dispatch('loadBatches', workspaceId)
    },

    async loadWorkspace({ commit, dispatch }, workspaceId) {
      const workspace = await dispatch('getWorkspace', workspaceId)
      await commit('SET_ACTIVE', workspace)
    },

    async loadBatches({ commit, dispatch }, workspaceId) {
      const workspaceBatches = await dispatch('gethWorkspaceBatches', workspaceId)

      const batches = workspaceBatches.map((batch) => {
        return { ...batch, selection: 0 }
      })
      await commit('SET_BATCHES', batches)
    },

    async reload({ state, rootState, getters, dispatch }) {
      if (state.active) {
        const activeWorkspace = { ...state.active }
        const activeBatch = rootState.batch.active
        await dispatch('unload', false)
        await dispatch('load', activeWorkspace.workspace_id)
        if (activeBatch) {
          const batch = getters['sampleBatch'](activeBatch.sample_batch_id)
          if (!batch) return
          batch.selection = 2
          await dispatch('batch/reload', batch, { root: true })
        }
      }
    },

    async unload({ rootState, commit, dispatch }, propagate = true) {
      if (!state.active) return
      rootState.api.emit('unsubscribe', state.active.workspace_id)
      await commit('SET_ACTIVE', null)
      await commit('SET_BATCHES', [])
      if (propagate) {
        await dispatch('batch/unload', true, { root: true })
        await dispatch('targets/unload', null, { root: true })
      }
    },
    // http client endpoints
    async getWorkspace({ dispatch }, workspaceId) {
      return await getApiData({
        dispatch,
        httpMethod: 'getWorkspace',
        requestData: workspaceId,
        errorMessage: `Failed to load workspace.`,
      })
    },
    async gethWorkspaceBatches({ dispatch }, workspaceId) {
      const batches = await getApiData({
        dispatch,
        httpMethod: 'getAllBatches',
        requestData: {
          workspace_id: workspaceId,
        },
        errorMessage: `Failed to load the workspace batches.`,
      })
      return batches.data
    },

    async createWorkspace({ rootState }, newWorkspace) {
      await rootState.api.httpClient.createWorkspace(newWorkspace)
    },

    async updateWorkspace({ rootState }, newWorkspace) {
      await rootState.api.httpClient.updateWorkspace(newWorkspace)
    },

    async deleteWorkspace({ dispatch, rootState }, workspace) {
      return await handleApiRequest({
        dispatch,
        rootState,
        httpMethod: 'deleteWorkspace',
        requestData: workspace,
        successNotificationType: 'deleted',
        successMessage: `Workspace ${workspace.workspace_name} was deleted successfully!`,
        errorMessage: `Failed to delete workspace ${workspace.workspace_name}. Please try again.`,
      })
    },

    // backend notifications
    async onWorkspaceReload({ dispatch }) {
      await dispatch('reload')
    },
  },
  getters: {
    sampleBatch: (state) => (sampleBatchId) => {
      const [sampleBatch] = state.batches.filter((batch) => batch.sample_batch_id == sampleBatchId)
      return sampleBatch ?? null
    },
    sampleBatches: (state) => {
      return state.batches ? state.batches : []
    },
    sampleBatchesSelected: (state, getters) => {
      return getters['sampleBatches'].filter((sampleBatch) => sampleBatch.selection >= 2)
    },
  },
}
