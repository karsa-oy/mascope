import { make } from "vuex-pathify";

const state = {
  active: null,
  // All Notifications
  inDevelopmentActive: false,
  batchComputeProgressActive: false,
  itemComputeProgressActive: false,
  // Compute progress notification
  progressMessage: "",
  progressPercentage: 0,
  computeError: false,
  // Item compute progress notification
  itemMatchComputing: false,
  // Batch compute progress notification
  batchMatchComputing: false,
  totalBatches: null,
  currentBatch: null,
  currentBatchMessage: "",
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

    SET_COMPUTE_ERROR(state, value) {
      state.computeError = value;
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
    // Item compute progress notification
    async onMatchItemUpdateComputeStarted({ commit }, data) {
      commit("SET_ITEM_MATCH_COMPUTING", true);
      commit(
        "SET_PROGRESS_MESSAGE",
        `Computing matches for "${data.sample_item_name}"`
      );
      commit("SET_PROGRESS_PERCENTAGE", 0);
    },
    async onMatchItemUpdateComputeProgress({ commit, state }, data) {
      if (data.progress_percentage) {
        commit("SET_PROGRESS_PERCENTAGE", data.progress_percentage);
      }
    },
    async onMatchItemUpdateComputeFinished({ commit }, data) {
      commit(
        "SET_PROGRESS_MESSAGE",
        `Computing matches for "${data.sample_item_name}" is finished`
      );
      commit("SET_PROGRESS_PERCENTAGE", 100);
      setTimeout(() => {
        // TODO_configuration move 500 animation delay to config file and 3000 closing notification time
        commit("SET_ITEM_MATCH_COMPUTING", false);
        setTimeout(() => {
          commit("SET_PROGRESS_MESSAGE", "");
          commit("SET_PROGRESS_PERCENTAGE", 0);
        }, 500);
      }, 3000);
    },
    async onMatchItemUpdateComputeFailed({ commit }, data) {
      commit(
        "SET_PROGRESS_MESSAGE",
        `Computing matches failed for "${data.sample_item_name}": ${data.errorMessage}`
      );
      commit("SET_COMPUTE_ERROR", true);
      setTimeout(() => {
        // TODO_configuration move 500 animation delay to config file and 3000 closing notification time
        commit("SET_ITEM_MATCH_COMPUTING", false);
        setTimeout(() => {
          commit("SET_PROGRESS_MESSAGE", "");
          commit("SET_PROGRESS_PERCENTAGE", 0);
          commit("SET_COMPUTE_ERROR", false);
        }, 500);
      }, 5000);
    },
  },
};
