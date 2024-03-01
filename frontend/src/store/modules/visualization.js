import { make } from "vuex-pathify";
import { handleApiRequest, getApiData, snakeToCamel } from "./apiHelper";

const state = {
  activeIon: null,
  activeIsotopes: null,
  // filter parameters
  paramMzTolerance: 0,
  paramMinIsotopeAbundance: 0,
  paramIsotopeRatioTolerance: 0,
  paramPeakMinIntensity: 0,
  paramMinIsotopeCorrelation: 0,
  paramProbableMatchThreshold: 0,
  paramPossibleMatchThreshold: 0,
  // chart data
  tracesSignalTimeseries: null,
  tracesSignalSumSpectrum: null,
};

// TODO_configuration Default filter parameters
const paramDefaults = {
  mz_tolerance: 15,
  min_isotope_abundance: 0.15,
  isotope_ratio_tolerance: 0.15,
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
    // data loading
    async load(
      { dispatch },
      { sampleId, ionId, collectionId, filterParams = null }
    ) {
      await dispatch("unload");
      await dispatch(
        "setFilterParams",
        filterParams ? filterParams : paramDefaults
      );

      await dispatch("loadMatches", { sampleId, ionId, collectionId });
      await dispatch("emitVisualization");
    },

    async loadMatches({ commit, dispatch, state }, params = null) {
      const sampleId = params?.sampleId || state.activeIon.sample_item_id;
      const ionId = params?.ionId || state.activeIon.target_ion_id;
      const collectionId =
        params?.collectionId || state.activeIon.target_collection_id;

      const sampleIonData = await dispatch("getSampleIonData", {
        sampleId,
        ionId,
        collectionId,
      });

      const existingIsotopes = state.activeIsotopes;

      const activeIsotopes = sampleIonData.match_isotopes.map((isotope) => {
        let existingIsotope = null;
        if (existingIsotopes) {
          existingIsotope = state.activeIsotopes.find(
            (existing) =>
              existing.target_isotope_id === isotope.target_isotope_id
          );
        }

        return {
          target_isotope_id: isotope.target_isotope_id,
          color: existingIsotope?.color || null, // Preserve color if exists
          mz: isotope.mz.toFixed(4),
          match_score: isotope.match_score,
          match_category: isotope.match_category,
          alarm_mode: isotope.alarm_mode,
          target_collection_type: isotope.target_collection_type,
          relative_abundance: isotope.relative_abundance,
          sample_peak_area: isotope.sample_peak_area,
          match_mz_error: isotope.match_mz_error,
          match_abundance_error: isotope.match_abundance_error,
          match_isotope_correlation: isotope.match_isotope_correlation,
        };
      });

      commit("SET_ACTIVE_ION", sampleIonData.match_ions[0]);
      commit("SET_ACTIVE_ISOTOPES", activeIsotopes);
    },

    async emitVisualization({ rootState, state, dispatch }, params) {
      const sampleId = params?.sampleId || state.activeIon.sample_item_id;
      const ionId = params?.ionId || state.activeIon.target_ion_id;

      if (state.tracesSignalTimeseries && state.tracesSignalSumSpectrum)
        await dispatch("resetVisualization");
      rootState.api.emit(
        "visualization_ion_focus",
        sampleId,
        ionId,
        state.paramMinIsotopeAbundance,
        state.paramPeakMinIntensity,
        state.paramMzTolerance
      );
    },

    async reload({ dispatch, state }) {
      await dispatch("loadMatches");
      await dispatch("emitVisualization");
    },

    async resetVisualization({ commit }) {
      if (!state.tracesSignalTimeseries && !state.tracesSignalSumSpectrum)
        return;
      await commit("SET_TRACES_SIGNAL_SUM_SPECTRUM", null);
      await commit("SET_TRACES_SIGNAL_TIMESERIES", null);
    },

    async unload({ state, commit, dispatch }) {
      // visualisation
      dispatch("resetVisualization");
      if (!state.activeIon) return;
      commit("SET_ACTIVE_ION", null);
      commit("SET_ACTIVE_ISOTOPES", null);
    },

    // parameters
    async setFilterParams({ commit }, params = null) {
      // Use provided params, then check if there is ion-specific filter params for that ion and sampleItem instrument
      const filterParams =
        params ||
        state?.activeIon?.filter_params?.[state.activeIon.instrument] ||
        {};

      // Use instrument-specific filter params or fallback to defaults
      for (const param in paramDefaults) {
        commit(
          `SET_PARAM_${param.toUpperCase()}`,
          filterParams[param] ?? paramDefaults[param]
        );
      }
    },
    async setDefaultFilterParams({ dispatch }) {
      await dispatch("setFilterParams", paramDefaults);
    },

    // http client endpoints
    async getSampleIonData(
      { rootGetters, state, dispatch },
      { sampleId, ionId, collectionId }
    ) {
      const alarmsList = rootGetters["targets/alarmsList"];

      const body = {
        target_ion_id: ionId,
        target_collection_id: collectionId,
        filter_params: {
          mz_tolerance: state.paramMzTolerance,
          isotope_ratio_tolerance: state.paramIsotopeRatioTolerance,
          peak_min_intensity: state.paramPeakMinIntensity,
          min_isotope_abundance: state.paramMinIsotopeAbundance,
          min_isotope_correlation: state.paramMinIsotopeCorrelation,
          probable_match_threshold: state.paramProbableMatchThreshold,
          possible_match_threshold: state.paramPossibleMatchThreshold,
        },
        alarms_list: alarmsList,
      };

      const sampleIonData = await getApiData({
        dispatch,
        httpMethod: "getSampleIonMatches",
        requestData: {
          sampleId,
          body,
        },
        errorMessage: `Failed to load sample ion data.`,
      });
      return sampleIonData.data;
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
    async saveFilterParams({ dispatch, state, rootState }) {
      const targetIonUpdate = {
        target_ion_id: state.activeIon.target_ion_id,
        target_ion_formula: state.activeIon.target_ion_formula,
        body: {
          filter_params: {
            [state.activeIon.instrument]: {
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
        target_ion_id: state.activeIon.target_ion_id,
        target_ion_formula: state.activeIon.target_ion_formula,
        body: {
          delete_instrument_filters: state.activeIon.instrument,
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

    // backend notifications
    async onVisualizationSignalSumSpectrum({ state, commit }, traces) {
      for (let trace of traces) {
        trace.x = new Float32Array(trace.x);
        trace.y = new Float32Array(trace.y);

        // Check if the trace has target_isotope_id and update the corresponding isotope in activeIsotopes
        if (trace.target_isotope_id) {
          const isotope = state.activeIsotopes.find(
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
    activeIsotopes: (state) => {
      return state.activeIsotopes ? state.activeIsotopes : [];
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
