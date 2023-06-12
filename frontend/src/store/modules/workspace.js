import { make } from "vuex-pathify";
import httpClient from "../../httpClient.js";

const state = {
  active: null,
  batches: [],
};

export default {
  namespaced: true,
  state,
  mutations: make.mutations(state),
  actions: {
    async load({ commit, rootState }, workspace) {
      rootState.api.emit("subscribe", workspace.workspace_id);
      const response = await httpClient.loadWorkspace(workspace.workspace_id);
      const batches = response.data.data.map((batch) => {
        return { ...batch, selection: 0 };
      });
      await commit("SET_BATCHES", batches);
      await commit("SET_ACTIVE", workspace);
    },
    async reload({ state, rootState, getters, dispatch }) {
      if (state.active) {
        const activeWorkspace = { ...state.active };
        const activeBatch = rootState.batch.active;
        await dispatch("unload", false);
        await dispatch("load", activeWorkspace);
        if (activeBatch) {
          const batch = getters["sampleBatch"](activeBatch.sample_batch_id);
          batch.selection = 2;
          await dispatch("batch/reload", batch, { root: true });
        }
      }
    },
    async unload({ rootState, commit, dispatch }, propagate = true) {
      if (!state.active) return;
      rootState.api.emit("unsubscribe", state.active.workspace_id);
      await commit("SET_ACTIVE", null);
      await commit("SET_BATCHES", []);
      if (propagate) await dispatch("batch/unload", true, { root: true });
    },
    // backend notifications
    async onWorkspaceReload({ dispatch }) {
      await dispatch("reload");
    },
  },
  getters: {
    sampleBatch: (state) => (sampleBatchId) => {
      const [sampleBatch] = state.batches.filter(
        (batch) => batch.sample_batch_id == sampleBatchId
      );
      return sampleBatch ?? null;
    },
  },
};
