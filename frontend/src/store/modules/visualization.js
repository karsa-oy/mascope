import { commit, dispatch, make } from "vuex-pathify";
import { handleApiRequest } from "./apiHelper";

const state = {
  // chart data
  tracesSignalTimeseries: null,
  tracesSignalSumSpectrum: null,
  isotopesInFocus: [],
};

export default {
  namespaced: true,
  state,
  mutations: {
    ...make.mutations(state),
  },
  actions: {
    async reset({ commit }) {
      await commit("SET_TRACES_SIGNAL_SUM_SPECTRUM", null);
      await commit("SET_TRACES_SIGNAL_TIMESERIES", null);
    },
    async submitMatchRating({ dispatch, rootState }, newMatchRating) {
      return await handleApiRequest({
        dispatch,
        rootState,
        httpMethod: "submitMatchRating",
        requestData: newMatchRating,
        successMessage:
          "Rating submitted successfully. Thanks for your feedback!",
        errorMessage: "Failed to submit rating. Please try again.",
      });
    },
    async onVisualizationSignalSumSpectrum({ state, commit }, traces) {
      for (let trace of traces) {
        trace.x = new Float32Array(trace.x);
        trace.y = new Float32Array(trace.y);

        // Check if the trace has target_isotope_id and update the corresponding isotope in isotopesInFocus
        if (trace.target_isotope_id) {
          const isotope = state.isotopesInFocus.find(
            (iso) => iso.target_isotope_id === trace.target_isotope_id
          );
          if (isotope) {
            // Extract RGB values and convert them to the 0-255 range
            const colorParts = trace.line.color.match(/(\d+\.?\d*)/g);
            if (colorParts) {
              const r = Math.round(parseFloat(colorParts[0]) * 255);
              const g = Math.round(parseFloat(colorParts[1]) * 255);
              const b = Math.round(parseFloat(colorParts[2]) * 255);
              isotope.color = `rgb(${r},${g},${b})`;
            }
          }
        }
      }
      const existingTraces = state.tracesSignalSumSpectrum;
      if (existingTraces) traces = [...existingTraces, ...traces];
      await commit("SET_TRACES_SIGNAL_SUM_SPECTRUM", traces);
    },
    async onVisualizationSignalTimeseries({ commit }, traces) {
      for (let trace of traces) {
        trace.x = new Float32Array(trace.x);
        trace.y = new Float32Array(trace.y);
      }
      const existingTraces = state.tracesSignalTimeseries;
      if (existingTraces) traces = [...existingTraces, ...traces];
      await commit("SET_TRACES_SIGNAL_TIMESERIES", traces);
    },
  },
  getters: {
    isotopesInFocus: (state) => {
      return state.isotopesInFocus ? state.isotopesInFocus : [];
    },
  },
};
