import { make } from "vuex-pathify";
import { getApiData } from "./apiHelper.js";

const state = {
  active: null,
  calibrationStatus: null,
  mzFit: null,
  mzFitError: null,
  mzFitStats: null,
  paramMatchScoreMin: 0,
  paramMinIsotopeAbundance: 0.1,
  paramMinPeakIntensity: 1000,
  paramRefineWindow: 100,
};

export default {
  namespaced: true,
  state,
  mutations: {
    ...make.mutations(state),
  },
  actions: {
    // data loading
    async load({ commit, dispatch }, sample) {
      // reset if previous calibration loaded
      if (state.active) {
        dispatch("unload");
      }
      const sampleMzCalibration = await dispatch(
        "getSampleMzCalibration",
        sample
      );
      await commit("SET_MZ_FIT", sampleMzCalibration);
    },

    async unload({ commit }) {
      await commit("SET_MZ_FIT", null);
      await commit("SET_MZ_FIT_ERROR", null);
      await commit("SET_MZ_FIT_STATS", null);
    },

    // http client endpoints
    async getSampleMzCalibration({ dispatch }, { sample_item_id }) {
      return await getApiData({
        dispatch,
        httpMethod: "getMzCalibration",
        requestData: {
          sample_item_id,
        },
        errorMessage: `Failed to get sample mz calibration.`,
      });
    },

    async calibrationMzFit({ dispatch }, requestData) {
      await getApiData({
        dispatch,
        httpMethod: "calibrationMzFit",
        requestData: requestData,
        errorMessage: `Failed to calibrate mz fit of sample ${requestData.sampleName}.`,
      });
    },

    async calibrationMzApply({ dispatch }, requestData) {
      await getApiData({
        dispatch,
        httpMethod: "calibrationMzApply",
        requestData: requestData,
        errorMessage: `Failed to apply mz calibration for sample file ${requestData.sample_filename}.`,
      });
    },
    async calibrationMzCalibrateSample({ rootState, rootGetters, dispatch }) {
      const sampleActive = rootState.sample.active;
      if (sampleActive) {
        await rootState.api.httpClient.calibrationMzCalibrateSample(
          {
            filename: sampleActive.filename,
            sample_item_id: sampleActive.sample_item_id,
            sample_item_name: sampleActive.sample_item_name,
            sample_batch_id: sampleActive.sample_batch_id,
          },
          rootGetters["calibration/params"]
        );
      } else {
        if (!rootState.instrument.scenthoundModeActive) return;
        setTimeout(() => {
          dispatch("calibrationMzCalibrateSample");
        }, 1000);
      }
    },

    // backend notifications
    // mz_fit
    async onCalibrationMzFitStarted({ commit, dispatch }, data) {
      dispatch("notification/onCalibrationStarted", data, { root: true });
    },
    async onCalibrationMzFitProgress({ commit, dispatch }, data) {
      dispatch("notification/onCalibrationProgress", data, { root: true });
    },
    async onCalibrationMzFitFinished({ commit, dispatch }, data) {
      let fit = data.fit;
      let fitError = data.error;
      let fitStats = data.stats;
      await commit("SET_MZ_FIT", fit);
      await commit("SET_MZ_FIT_ERROR", fitError);
      await commit("SET_MZ_FIT_STATS", fitStats);
      dispatch("notification/onCalibrationFinished", data, { root: true });
    },
    async onCalibrationMzFitFailed({ commit, dispatch }, data) {
      dispatch("notification/onCalibrationFailed", data, { root: true });
    },

    // mz_apply
    async onCalibrationMzApplyStarted({ dispatch }, data) {
      dispatch("notification/onCalibrationStarted", data, { root: true });
    },
    async onCalibrationMzApplyFinished({ rootState, dispatch }, data) {
      if (data.autosampler_mode === true) {
        dispatch("notification/onCalibrationFinished", data, { root: true });
      } else {
        await dispatch("unload");
        await dispatch("sample/reload", rootState.sample.active, {
          root: true,
        });
        await dispatch("batch/reload", null, { root: true });
        dispatch("notification/onCalibrationFinished", data, { root: true });
      }
    },

    // mz_calibrate_sample
    async onCalibrationMzCalibrateSampleStarted({ rootState, commit }, data) {
      commit("SET_CALIBRATION_STATUS", data);
    },
    async onCalibrationMzCalibrateSampleProgress({ rootState, commit }, data) {
      commit("SET_CALIBRATION_STATUS", data);
    },
    async onCalibrationMzCalibrateSampleFinished(
      { rootState, commit, dispatch },
      data
    ) {
      commit("SET_CALIBRATION_STATUS", data);
      // Start matching in Scenthound automatically
      if (rootState.instrument.scenthoundModeActive) {
        dispatch("instrument/matchSample", null, { root: true });
      }
    },
    async onCalibrationMzCalibrateSampleFailed({ rootState, commit }, data) {
      commit("SET_CALIBRATION_STATUS", { ...data, failed: true });
    },

    // mz_calibrate_batch
    async onCalibrationMzCalibrateBatchStarted(
      { rootState, commit, dispatch },
      data
    ) {
      dispatch("notification/onCalibrationStarted", data, { root: true });
    },
    async onCalibrationMzCalibrateBatchFinished(
      { rootState, commit, dispatch },
      data
    ) {
      dispatch("notification/onCalibrationFinished", data, { root: true });
    },
    // TODO_notifications  move to notification store, use the onActionFinished,
    // failed_calibration_samples is not used now from import_sample_items
    async onCalibrationMzCalibrateBatchFailed(
      { rootState, commit, dispatch },
      data
    ) {
      const showWarningFailedCalibration = (payload) => {
        dispatch("notification/showWarningNotification", payload, {
          root: true,
        });
        commit("notification/RESET_CALIBRATION_NOTIFICATION", null, {
          root: true,
        });
      };
      const failedCalibrationSamples = () => {
        const payload = {
          notification: "failedCalibrationSamples",
          data: data.samples,
        };
        if (rootState.notification.active) {
          setTimeout(() => {
            showWarningFailedCalibration(payload);
          }, 2000);
        } else {
          showWarningFailedCalibration(payload);
        }
      };

      const regularFail = () => {
        dispatch("notification/onCalibrationFailed", data, { root: true });
      };

      if (data.type === "failed_calibration_samples") {
        failedCalibrationSamples();
      } else {
        regularFail();
      }
    },
  },
  getters: {
    params: (state) => {
      return {
        match_score_min: state.paramMatchScoreMin,
        refine_window: state.paramRefineWindow,
        peak_intensity_min: state.paramMinPeakIntensity,
        isotope_abundance_min: state.paramMinIsotopeAbundance,
      };
    },
  },
};
