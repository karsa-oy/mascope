import { make } from "vuex-pathify";
import { getApiData, extractDistinctValues } from "./apiHelper.js";

const mode = import.meta.env.MASCOPE_PUBLIC_MODE;

const state = {
  attributeTemplates: [],
  instruments: [],
  ionMechanisms: [],
  mode: mode,
  pushNotification: null,
  ready: false,
  workspaces: [],
};
export default {
  namespaced: true,
  state,
  mutations: make.mutations(state),
  actions: {
    // data loading
    async load({ commit, dispatch, rootState }) {
      const api = rootState.api;

      // load attribute templates
      const attributeTemplates = await dispatch("getAllAttributeTemplates");
      await commit("SET_ATTRIBUTE_TEMPLATES", attributeTemplates);

      // load instruments
      const instrumentFunctions = await dispatch("getAllInstrumentFunctions");
      const instruments = extractDistinctValues(
        instrumentFunctions,
        "instrument"
      );
      await commit("SET_INSTRUMENTS", instruments);

      // Load ionization mechanisms
      const ionizationMechanisms = await dispatch("getAllIonizationMechanisms");
      await commit("SET_ION_MECHANISMS", ionizationMechanisms);

      // load workspaces
      const workspaces = await dispatch("getAllWorkspaces");
      await commit("SET_WORKSPACES", workspaces);

      // set application ready to stop loading spinner and show app
      commit("SET_READY", true);
    },
    async reload({ dispatch }) {
      dispatch("load");
    },

    // http client endpoints
    async getAllAttributeTemplates({ dispatch }) {
      const attributeTemplatesData = await getApiData({
        dispatch,
        httpMethod: "getAllAttributeTemplates",
        errorMessage: `Failed to load attribute templates.`,
      });

      return attributeTemplatesData.data;
    },
    async getAllInstrumentFunctions({ dispatch }) {
      const instrumentFunctions = await getApiData({
        dispatch,
        httpMethod: "getAllInstrumentFunctions",
        errorMessage: `Failed to load instrument functions.`,
      });

      return instrumentFunctions.data;
    },
    async getAllIonizationMechanisms({ dispatch }) {
      const ionizationMechanisms = await getApiData({
        dispatch,
        httpMethod: "getAllIonizationMechanisms",
        errorMessage: `Failed to load ionization mechanisms.`,
      });

      return ionizationMechanisms.data;
    },
    async getAllWorkspaces({ dispatch }) {
      const workspaces = await getApiData({
        dispatch,
        httpMethod: "getAllWorkspaces",
        errorMessage: `Failed to load workspaces.`,
      });

      return workspaces.data;
    },
    // backend notifications
    async onOrgReload({ dispatch }) {
      dispatch("reload");
    },
    async pushNotification({ commit }, message) {
      commit("SET_PUSH_NOTIFICATION", message);
    },
  },
};
