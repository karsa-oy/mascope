import { make } from "vuex-pathify";
import { getApiData } from "./apiHelper.js";

const state = {
  active: null,
  acquisitionActiveFilename: null,
  acquisitionProgress: 0,
  acquisitions: null,
  conversionProgress: 0,
  matchingProgress: 0,
  mzCalibration: null,
  recentAcquisitions: null,
  sampleItemPending: null,
  scenthoundModeActive: false,
};

export default {
  namespaced: true,
  state,
  mutations: make.mutations(state),
  actions: {
    // data loading
    async load({ rootState, commit, dispatch }, instrument) {
      if (state.active) await dispatch("unload");
      rootState.api.emit("subscribe", instrument);
      await commit("SET_ACTIVE", instrument);
      await dispatch("getMzCalibration");
      await dispatch("getRecentAcquisitions");
    },

    async getMzCalibration({ commit, dispatch }) {
      const mzCalibration = await dispatch("getLastMzCalibration");
      commit("SET_MZ_CALIBRATION", mzCalibration);
    },

    async getAcquisitions({ commit, dispatch }, datetimeRange) {
      const sampleFiles = await dispatch("getSampleFiles", datetimeRange);
      commit("SET_ACQUISITIONS", sampleFiles);
    },

    async getRecentAcquisitions({ commit, dispatch }) {
      const sampleFiles = await dispatch("getRecentSampleFiles");
      commit("SET_RECENT_ACQUISITIONS", sampleFiles);
    },

    async resetAcquisitionStatus({ commit }) {
      commit("SET_ACQUISITION_ACTIVE_FILENAME", null);
      commit("SET_ACQUISITION_PROGRESS", 0);
      commit("calibration/SET_CALIBRATION_STATUS", null, { root: true });
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

    async matchSample({ rootState, dispatch }) {
      const sampleActive = rootState.sample.active;
      const calibrationVerified =
        rootState.sample.active.mz_calibration.verified;
      if (sampleActive && calibrationVerified) {
        await dispatch("sample/matchItemCompute", sampleActive, { root: true });
      } else {
        // Try again in 1 second if scenthound is still opened
        if (!state.scenthoundModeActive) return;
        setTimeout(() => {
          dispatch("matchSample");
        }, 1000);
      }
    },

    // http client endpoints
    async getSampleFiles({ state, dispatch }, datetimeRange) {
      const minDatetime = datetimeRange.min.toISOString();
      const maxDatetime = datetimeRange.max.toISOString();

      const reqData = {
        minDatetime,
        maxDatetime,
        instrument: state.active,
        sort: "datetime_utc",
        order: "asc",
      };

      const sampleFiles = await getApiData({
        dispatch,
        httpMethod: "getAllSampleFiles",
        requestData: reqData,
        errorMessage: `Failed to get all sample files.`,
      });

      return sampleFiles.data;
    },

    async getRecentSampleFiles({ state, dispatch }) {
      const reqData = {
        instrument: state.active,
        sort: "datetime_utc",
        order: "asc",
      };

      const sampleFiles = await getApiData({
        dispatch,
        httpMethod: "getRecentSampleFiles",
        requestData: reqData,
        errorMessage: `Failed to get recent acquisitions.`,
      });

      return sampleFiles.data;
    },

    async getLastMzCalibration({ state, dispatch }) {
      const reqData = {
        instrument: state.active,
      };

      const mzCalibration = await getApiData({
        dispatch,
        httpMethod: "getMzCalibration",
        requestData: reqData,
        errorMessage: `Failed to get last mz calibration.`,
      });

      return mzCalibration;
    },
    // backend notifications
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
    async onInstrumentConversionFinished({ state, commit, dispatch }, data) {
      commit("SET_CONVERSION_PROGRESS", data.progress);
      // Wait for sample to be saved, then start mass calibration
      if (state.scenthoundModeActive) {
        dispatch("calibration/calibrationMzCalibrateSample", null, {
          root: true,
        });
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
    async onSampleFileCreated({ state, dispatch, commit }, filename) {
      await dispatch("getRecentAcquisitions");
      if (state.scenthoundModeActive) {
        if (state.sampleItemPending) {
          await dispatch("sample/create", state.sampleItemPending, {
            root: true,
          });
          commit("SET_SAMPLE_ITEM_PENDING", null);
        }
      }
    },
  },
  getters: {},
};
