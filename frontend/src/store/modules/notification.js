import { make } from "vuex-pathify";

const state = {
  active: null,
  // All Notifications
  warningActive: false,
  generalActive: false,
  batchComputeProgressActive: false,
  itemComputeProgressActive: false,
  calibrationProgressActive: false,
  // warning notifications
  warningNotification: null,
  warningData: null,
  // general notifications
  generalNotification: null,
  generalNotificationMessage: null,
  // Compute progress notification
  progressMessage: "",
  progressPercentage: 0,
  // Item compute progress notification
  itemMatchComputing: false,
  // Batch compute progress notification
  batchMatchComputing: false,
  totalBatches: null,
  currentBatch: null,
  currentBatchMessage: "",
  // Calibration progress notification
  calibrationComputing: false,
  calibrationAction: null,
  // Errors
  computeError: false,
  calibrationError: false,
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
    RESET_WARNING_NOTIFICATION(state) {
      state.warningNotification = null;
      state.warningData = null;
    },
    RESET_GENERAL_NOTIFICATION(state) {
      state.generalNotification = null;
      state.generalNotificationMessage = null;
    },
    RESET_CALIBRATION_NOTIFICATION(state) {
      state.progressMessage = "";
      state.progressPercentage = 0;
      state.calibrationError = false;
      state.calibrationAction = null;
    },
  },
  actions: {
    // warning notification
    showWarningNotification({ commit }, payload) {
      commit("SET_WARNING_NOTIFICATION", payload.notification);
      commit("SET_WARNING_DATA", payload?.data || null);
      commit("activate", { notification: "warning" });
    },
    showGeneralNotification({ dispatch, commit }, payload) {
      commit("SET_GENERAL_NOTIFICATION", payload.notification);
      commit("SET_GENERAL_NOTIFICATION_MESSAGE", payload.message);
      commit("activate", { notification: "general" });
    },
    // backend listeners
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
    async onMatchBatchComputeFinished({ commit, state, dispatch }, data) {
      let progressMessage = `Finished computation for ${
        state.totalBatches
      } batch${state.totalBatches === 1 ? "" : "es"}`;

      if (
        data.samples_compute_failed &&
        data.samples_compute_failed.length > 0
      ) {
        commit("SET_COMPUTE_ERROR", true);
        progressMessage += ` with ${data.samples_compute_failed.length} sample${
          data.samples_compute_failed.length === 1 ? "" : "s"
        } failed to compute matches`;

        // Show warning notification after 3 seconds with info about failed to compute matches samples
        setTimeout(() => {
          dispatch("showWarningNotification", {
            notification: "batchComputeFailedSamples",
            data: data.samples_compute_failed,
          });
        }, 4000);
      }

      commit("SET_PROGRESS_MESSAGE", progressMessage);
      commit("SET_CURRENT_BATCH_MESSAGE", "");
      commit("SET_PROGRESS_PERCENTAGE", 100);
      setTimeout(() => {
        // TODO_configuration move 500 animation delay to config file and 3000 closing notification time
        commit("SET_BATCH_MATCH_COMPUTING", false);
        commit("SET_TOTAL_BATCHES", null);
        commit("SET_CURRENT_BATCH", null);
        setTimeout(() => {
          commit("SET_PROGRESS_MESSAGE", "");
          commit("SET_COMPUTE_ERROR", false);
          commit("SET_PROGRESS_PERCENTAGE", 0);
        }, 500);
      }, 4000);
    },
    // Item compute progress notification
    async onMatchItemUpdateComputeStarted({ commit }, data) {
      commit("RESET_CALIBRATION_NOTIFICATION");
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
    async onMatchItemUpdateComputeFailed({ dispatch, commit }, data) {
      commit(
        "SET_PROGRESS_MESSAGE",
        `Computing matches failed for "${data.sample_item_name}"`
      );
      commit("SET_PROGRESS_PERCENTAGE", 100);
      commit("SET_COMPUTE_ERROR", true);
      setTimeout(() => {
        // Show warning notification after 3 seconds with info about failed to compute matches samples
        dispatch("showWarningNotification", {
          notification: "itemComputeFailed",
          data: data.errorMessage,
        });
        // TODO_configuration move 500 animation delay to config file and 3000 closing notification time
        commit("SET_ITEM_MATCH_COMPUTING", false);
        setTimeout(() => {
          commit("SET_PROGRESS_MESSAGE", "");
          commit("SET_PROGRESS_PERCENTAGE", 0);
          commit("SET_COMPUTE_ERROR", false);
        }, 500);
      }, 3000);
    },
    // calibration notifications
    async onCalibrationStarted({ commit }, data) {
      commit("SET_CALIBRATION_COMPUTING", true);
      commit("SET_CALIBRATION_ACTION", data.action);
      commit(
        "SET_PROGRESS_MESSAGE",
        `Calibration process started: ${data.action}...`
      );
      commit("SET_PROGRESS_PERCENTAGE", data.progress_percentage);
    },
    async onCalibrationProgress({ commit }, data) {
      if (data.progress_percentage) {
        commit("SET_PROGRESS_PERCENTAGE", data.progress_percentage);
      }
    },
    async onCalibrationFinished({ commit }, data) {
      commit(
        "SET_PROGRESS_MESSAGE",
        `Calibration process finished: ${data.action}...`
      );
      commit("SET_PROGRESS_PERCENTAGE", data.progress_percentage || 100);
      setTimeout(() => {
        if (state.calibrationAction !== data.action) {
          return; // Do not close if this is not the currently active action.
        }
        commit("SET_CALIBRATION_COMPUTING", false);
        setTimeout(() => {
          if (!state.calibrationProgressActive) return;
          commit("RESET_CALIBRATION_NOTIFICATION");
        }, 500);
      }, 3000);
    },
    async onCalibrationFailed({ commit }, data) {
      commit(
        "SET_PROGRESS_MESSAGE",
        `Calibration process ${data.action} failed: ${data.error}`
      );
      commit("SET_CALIBRATION_ERROR", true);
      setTimeout(() => {
        // TODO_configuration move 500 animation delay to config file and 3000 closing notification time
        commit("SET_CALIBRATION_COMPUTING", false);
        setTimeout(() => {
          commit("RESET_CALIBRATION_NOTIFICATION");
        }, 500);
      }, 5000);
    },
  },
};
