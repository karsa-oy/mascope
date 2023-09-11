import { make } from "vuex-pathify";

const state = {
  active: null,
  // All Notifications
  inDevelopmentActive: false,
  batchComputeProgressActive: false,
  // Batch compute progress notification
  batchMatchComputing: false,
  totalBatches: null,
  currentBatch: null,
  progressMessage: "",
  currentBatchMessage: "",
  progressPercentage: 0,
};

export default {
  namespaced: true,
  state,
  mutations: {
    ...make.mutations(state),

    activate(state, { notification }) {
      if (state.active) {
        state[state.active + "Active"] = false;
      }
      state.active = notification;
      state[notification + "Active"] = true;
    },
    deactivate(state) {
      if (state.active) {
        state[state.active + "Active"] = false;
      }
      state.active = null;
    },
  },
  actions: {
    // backend notifications
    // Batch compute progress notification
    async onMatchBatchComputeStarted({ commit }, data) {
      commit("SET_BATCH_MATCH_COMPUTING", true);
      commit("SET_TOTAL_BATCHES", data.total_batches);
      commit(
        "SET_PROGRESS_MESSAGE",
        `Changes in workspace detected.
        Starting computation for ${data.total_batches} batches`
      );
    },
    async onMatchBatchComputeProgress({ commit, state }, data) {
      if (data.current_batch) {
        commit("SET_CURRENT_BATCH", data.current_batch);
        commit(
          "SET_PROGRESS_MESSAGE",
          `Changes in workspace detected.
          Computing matches for sample batch ${data.current_batch} / ${state.totalBatches}`
        );
      }
      if (data.current_batch_message) {
        commit("SET_CURRENT_BATCH_MESSAGE", data.current_batch_message);
      } else {
        commit("SET_CURRENT_BATCH_MESSAGE", "");
      }
    },
    async onMatchBatchComputeProgressPercentage({ commit }, data) {
      if (data.progress_percentage) {
        commit("SET_PROGRESS_PERCENTAGE", data.progress_percentage);
      }
    },
    async onMatchBatchComputeFinished({ commit, state, dispatch }) {
      commit(
        "SET_PROGRESS_MESSAGE",
        `Finished computation for ${state.totalBatches} batches`
      );
      commit("SET_CURRENT_BATCH_MESSAGE", "");
      commit("SET_PROGRESS_PERCENTAGE", 100);
      setTimeout(() => {
        // TODO_configuration move 500 animation delay to config file and 3000 closing notification time
        commit("SET_BATCH_MATCH_COMPUTING", false);
        commit("SET_TOTAL_BATCHES", null);
        commit("SET_CURRENT_BATCH", null);
        setTimeout(() => {
          commit("SET_PROGRESS_MESSAGE", "");
          commit("SET_PROGRESS_PERCENTAGE", 0);
        }, 500);
      }, 3000);
    },
  },
};
