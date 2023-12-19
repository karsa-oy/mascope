import { commit, dispatch, make } from "vuex-pathify";
import { handleApiRequest, snakeToCamel } from "./apiHelper";

const state = {
  // chart data
  tracesSignalTimeseries: null,
  tracesSignalSumSpectrum: null,
  ionInFocus: {},
  isotopesInFocus: [],
  // filter parameters
  paramMzTolerance: 0,
  paramMinIsotopeAbundance: 0,
  paramIsotopeRatioTolerance: 0,
  paramPeakMinIntensity: 0,
  paramMinIsotopeCorrelation: 0,
  paramProbableMatchThreshold: 0,
  paramPossibleMatchThreshold: 0,
};

// TODO_configuration Default filter parameters
const paramDefaults = {
  mz_tolerance: 15,
  min_isotope_abundance: 0.15,
  isotope_ratio_tolerance: 0.1,
  peak_min_intensity: 0,
  min_isotope_correlation: 0.8,
  probable_match_threshold: 0.8,
  possible_match_threshold: 0.7,
};

export default {
  namespaced: true,
  state,
  mutations: {
    ...make.mutations(state),
  },
  actions: {
    async emitVisualization(
      { rootState, state, dispatch },
      { sampleId, ionId }
    ) {
      if (state.tracesSignalTimeseries && state.tracesSignalSumSpectrum)
        await dispatch("reset");
      rootState.api.emit(
        "visualization_ion_focus",
        sampleId,
        ionId,
        state.paramMinIsotopeAbundance,
        state.paramPeakMinIntensity,
        state.paramMzTolerance
      );
    },
    async reset({ commit }) {
      await commit("SET_TRACES_SIGNAL_SUM_SPECTRUM", null);
      await commit("SET_TRACES_SIGNAL_TIMESERIES", null);
    },

    async reloadMatches({ dispatch, state }) {
      const reqData = {
        sample_item_id: state.ionInFocus.sample_item_id,
        target_ion_id: state.ionInFocus.target_ion_id,
        filter_params: {
          mz_tolerance: state.paramMzTolerance,
          isotope_ratio_tolerance: state.paramIsotopeRatioTolerance,
          peak_min_intensity: state.paramPeakMinIntensity,
          min_isotope_abundance: state.paramMinIsotopeAbundance,
          min_isotope_correlation: state.paramMinIsotopeCorrelation,
          probable_match_threshold: state.paramProbableMatchThreshold,
          possible_match_threshold: state.paramPossibleMatchThreshold,
        },
      };
      await dispatch("getSampleIonMatches", reqData);
    },
    async setFilterParams({ commit }, params = null) {
      // Use provided params, then check if there is ion-specific filter params for that ion and sampleItem instrument
      const filterParams =
        params ||
        state.ionInFocus.filter_params?.[state.ionInFocus.instrument] ||
        {};

      // Use instrument-specific filter params or fallback to defaults
      for (const param in paramDefaults) {
        commit(
          `SET_PARAM_${param.toUpperCase()}`,
          filterParams[param] || paramDefaults[param]
        );
      }
    },
    async setDefaultFilterParams({ dispatch }) {
      await dispatch("setFilterParams", paramDefaults);
    },

    // http client endpoints
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
    async saveFilterParams({ dispatch, state, rootState }) {
      const targetIonUpdate = {
        target_ion_id: state.ionInFocus.target_ion_id,
        target_ion_formula: state.ionInFocus.target_ion_formula,
        body: {
          filter_params: {
            [state.ionInFocus.instrument]: {
              mz_tolerance: state.paramMzTolerance,
              isotope_ratio_tolerance: state.paramIsotopeRatioTolerance,
              peak_min_intensity: state.paramPeakMinIntensity,
              min_isotope_abundance: state.paramMinIsotopeAbundance,
              min_isotope_correlation: state.paramMinIsotopeCorrelation,
              probable_match_threshold: state.paramProbableMatchThreshold,
              possible_match_threshold: state.paramPossibleMatchThreshold,
            },
          },
        },
      };
      return await handleApiRequest({
        dispatch,
        rootState,
        httpMethod: "updateTargetIon",
        requestData: targetIonUpdate,
        successMessage: `Filtering parameters for ${targetIonUpdate.target_ion_formula} saved successfully!`,
        errorMessage: "Failed to save filtering parameters. Please try again.",
      });
    },
    async deleteInstrumentFilterParams({ dispatch, state, rootState }) {
      const targetIonUpdate = {
        target_ion_id: state.ionInFocus.target_ion_id,
        target_ion_formula: state.ionInFocus.target_ion_formula,
        body: {
          delete_instrument_filters: state.ionInFocus.instrument,
        },
      };
      return await handleApiRequest({
        dispatch,
        rootState,
        httpMethod: "updateTargetIon",
        requestData: targetIonUpdate,
        successMessage: `Filtering parameters for ${targetIonUpdate.body.delete_instrument_filters} instrument were deleted successfully!`,
        errorMessage:
          "Failed to delete filtering parameters. Please try again.",
      });
    },
    async getSampleIonMatches({ commit, state, rootState }, reqData) {
      const response = await rootState.api.httpClient.getSampleIonMatches(
        reqData.sample_item_id,
        { ...reqData }
      );

      const isotopesInFocus = response.data.data.match_isotopes.map(
        (isotope) => {
          const existingIsotope = state.isotopesInFocus.find(
            (existing) =>
              existing.target_isotope_id === isotope.target_isotope_id
          );

          return {
            target_isotope_id: isotope.target_isotope_id,
            color: existingIsotope?.color || "rgb(48,162,218)", // Preserve color if exists
            mz: isotope.mz.toFixed(4),
            match_score: isotope.match_score,
            match_category: isotope.match_category,
            relative_abundance: isotope.relative_abundance,
            sample_peak_area: isotope.sample_peak_area,
            match_mz_error: isotope.match_mz_error,
            match_abundance_error: isotope.match_abundance_error,
            match_isotope_correlation: isotope.match_isotope_correlation,
          };
        }
      );

      commit("SET_ISOTOPES_IN_FOCUS", isotopesInFocus);
      commit("SET_ION_IN_FOCUS", response.data.data.match_ions[0]);
    },
    // backend notifications
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
    defaultFilterParams: (state) => {
      // Transform paramDefaults keys to camelCase and prepend 'param'
      const transformedParamDefaults = Object.entries(paramDefaults).reduce(
        (acc, [key, value]) => {
          // Prepend 'param' and convert to camelCase
          const camelCaseKey =
            "param" + snakeToCamel(key.charAt(0).toUpperCase() + key.slice(1));
          acc[camelCaseKey] = value;
          return acc;
        },
        {}
      );
      return transformedParamDefaults;
    },
  },
};
