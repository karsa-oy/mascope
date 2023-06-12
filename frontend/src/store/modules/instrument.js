import { dispatch, make } from "vuex-pathify";
import httpClient from "../../httpClient.js";

const state = {
  active: null,
  calibrationStatus: null,
  acquisitionActiveFilename: null,
  acquisitionProgress: 0,
  acquisitions: null,
  conversionProgress: 0,
  matchingProgress: 0,
  mzCalibration: null,
  recentAcquisitions: null,
  scenthoundModeActive: false,
};

export default {
  namespaced: true,
  state,
  mutations: make.mutations(state),
  actions: {
    async getAcquisitions({ state, commit }, datetimeRange) {
      const minDatetime = datetimeRange.min.toISOString();
      const maxDatetime = datetimeRange.max.toISOString();

      const response = await httpClient.getAllSampleFiles({
        minDatetime,
        maxDatetime,
        instrument: state.active,
        sort: "datetime_utc",
        order: "asc",
      });
      commit("SET_ACQUISITIONS", response.data.data);
    },
    async getRecentAcquisitions({ state, commit }) {
      const response = await httpClient.getRecentSampleFiles({
        instrument: state.active,
        sort: "datetime_utc",
        order: "asc",
      });
      commit("SET_RECENT_ACQUISITIONS", response.data.data);
    },
    async getMzCalibration({ state, commit }) {
      const response = await httpClient.getLastMzCalibration({
        instrument: state.active,
      });
      const mz_calibration = response.data ? response.data : null;
      commit("SET_MZ_CALIBRATION", mz_calibration);
    },
    async load({ rootState, commit, dispatch }, instrument) {
      if (state.active) await dispatch("unload");
      rootState.api.emit("subscribe", instrument);
      await commit("SET_ACTIVE", instrument);
      await dispatch("getMzCalibration");
      await dispatch("getRecentAcquisitions");
    },
    async matchSample({ rootState, dispatch }) {
      const sampleActive = rootState.sample.active;
      if (sampleActive) {
        rootState.api.emit("match_item_compute", {
          filename: sampleActive.filename,
          sample_item_id: sampleActive.sample_item_id,
          sample_batch_id: sampleActive.sample_batch_id,
        });
      } else {
        // Try again in 1 second
        setTimeout(() => {
          dispatch("matchSample");
        }, 1000);
      }
    },
    async mzCalibrateSample({ rootState, rootGetters, dispatch }) {
      const sampleActive = rootState.sample.active;
      if (sampleActive) {
        rootState.api.emit(
          "calibration_mz_calibrate_sample",
          {
            filename: sampleActive.filename,
            sample_item_id: sampleActive.sample_item_id,
            sample_batch_id: sampleActive.sample_batch_id,
          },
          rootGetters["calibration/params"]
        );
      } else {
        // Try again in 1 second
        setTimeout(() => {
          dispatch("mzCalibrateSample");
        }, 1000);
      }
    },
    async resetAcquisitionStatus({ commit }) {
      commit("SET_ACQUISITION_ACTIVE_FILENAME", null);
      commit("SET_ACQUISITION_PROGRESS", 0);
      commit("SET_CALIBRATION_STATUS", null);
      commit("SET_CONVERSION_PROGRESS", 0);
      commit("SET_MATCHING_PROGRESS", 0);
    },
    async unload({ rootState, state, commit, dispatch }) {
      if (!state.active) return;
      rootState.api.emit("unsubscribe", state.active);
      commit("SET_ACTIVE", null);
      commit("SET_MZ_CALIBRATION", null);
      commit("SET_ACQUISITIONS", null);
      commit("SET_RECENT_ACQUISITIONS", null);
      await dispatch("resetAcquisitionStatus");
      commit("SET_SCENTHOUND_MODE_ACTIVE", false);
    },
    // notifications
    async onInstrumentAcquisitionFinished({ commit }, data) {
      commit("SET_ACQUISITION_ACTIVE_FILENAME", data.filename);
      commit("SET_ACQUISITION_PROGRESS", data.progress);
    },
    async onInstrumentAcquisitionProgress({ commit }, data) {
      commit("SET_ACQUISITION_ACTIVE_FILENAME", data.filename);
      commit("SET_ACQUISITION_PROGRESS", data.progress);
    },
    async onInstrumentAcquisitionStarted(
      { rootState, commit, dispatch },
      data
    ) {
      await dispatch("sample/unload", null, { root: true });
      await dispatch("resetAcquisitionStatus");
      commit("SET_ACQUISITION_ACTIVE_FILENAME", data.filename);
      commit("SET_ACQUISITION_PROGRESS", data.progress);
    },
    async onCalibrationMzCalibrateFailed({ commit }, data) {
      commit("SET_CALIBRATION_STATUS", { ...data, failed: true });
    },
    async onCalibrationMzCalibrateFinished({ state, commit }, data) {
      commit("SET_CALIBRATION_STATUS", data);
      // Start matching
      if (state.scenthoundModeActive) {
        dispatch("instrument/matchSample", null, { root: true });
      }
    },
    async onCalibrationMzCalibrateProgress({ commit }, data) {
      commit("SET_CALIBRATION_STATUS", data);
    },
    async onCalibrationMzCalibrateStarted({ commit }, data) {
      commit("SET_CALIBRATION_STATUS", data);
    },
    async onInstrumentConversionFinished({ state, commit, dispatch }, data) {
      commit("SET_CONVERSION_PROGRESS", data.progress);
      // Wait for sample to be saved, then start mass calibration
      if (state.scenthoundModeActive) {
        dispatch("mzCalibrateSample");
      }
    },
    async onInstrumentConversionProgress({ commit }, data) {
      commit("SET_CONVERSION_PROGRESS", data.progress);
    },
    async onInstrumentConversionStarted({ commit }, data) {
      commit("SET_CONVERSION_PROGRESS", data.progress);
    },
    async onMatchItemComputeFailed({ commit }, data) {
      commit("SET_MATCHING_PROGRESS", data.progress);
    },
    async onMatchItemComputeFinished({ commit }, data) {
      commit("SET_MATCHING_PROGRESS", data.progress);
      // TODO: case: background, verify interferences
      // TODO: case: else, display matches
    },
    async onMatchItemComputeProgress({ commit }, data) {
      commit("SET_MATCHING_PROGRESS", data.progress);
    },
    async onMatchItemComputeStarted({ commit }, data) {
      commit("SET_MATCHING_PROGRESS", data.progress);
    },
    async onSampleFileCreated({ rootState, dispatch }, filename) {
      await dispatch("api/reloadDb", null, { root: true });
      await dispatch("getRecentAcquisitions");
    },
  },
  getters: {},
};
