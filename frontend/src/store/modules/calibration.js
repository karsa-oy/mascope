import { make } from "vuex-pathify";
import { loadFromApi } from "./apiHelper.js";

const state = {
  active: null,
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
    async load({ commit, rootState }, sample) {
      // reset if previous calibration loaded
      if (state.active) {
        dispatch("unload");
      }
      const sampleItemId = sample.sample_item_id;
      const response = await rootState.api.httpClient.getSampleMzCalibration(
        sampleItemId
      );
      await commit("SET_MZ_FIT", response.data);
    },
    async unload({ commit }) {
      await commit("SET_MZ_FIT", null);
      await commit("SET_MZ_FIT_ERROR", null);
      await commit("SET_MZ_FIT_STATS", null);
    },
    async onCalibrationMzApplied({ dispatch }, sample_item_id) {
      await dispatch("unload");
      dispatch("batch/reload", null, { root: true });
    },
    async onCalibrationMzFitStats({ commit }, response) {
      let fit = response.fit;
      let fitError = response.error;
      let fitStats = response.stats;
      await commit("SET_MZ_FIT", fit);
      await commit("SET_MZ_FIT_ERROR", fitError);
      await commit("SET_MZ_FIT_STATS", fitStats);
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
