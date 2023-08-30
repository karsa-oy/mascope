import { make } from "vuex-pathify";
import { loadFromApi, extractDistinctValues } from "./apiHelper.js";

const mode = import.meta.env.MASCOPE_PUBLIC_MODE;

const state = {
  attributeTemplates: [],
  instruments: [],
  ionMechanisms: [],
  mode: mode,
  pushNotification: null,
  ready: false,
  schema: {},
  // targetCollections: [],
  workspaces: [],
};
export default {
  namespaced: true,
  state,
  mutations: make.mutations(state),
  actions: {
    async load({ commit, dispatch, rootState }) {
      const api = rootState.api;
      // load attribute templates
      await loadFromApi(
        api.httpClient.getAllAttributeTemplates,
        "SET_ATTRIBUTE_TEMPLATES",
        commit
      );

      // load instruments
      await loadFromApi(
        api.httpClient.getAllInstrumentFunctions,
        "SET_INSTRUMENTS",
        commit,
        (instruments) => extractDistinctValues(instruments, "instrument")
      );

      // Load ionization mechanisms
      await loadFromApi(
        api.httpClient.getAllIonizationMechanisms,
        "SET_ION_MECHANISMS",
        commit
      );

      // load workspaces
      await loadFromApi(
        api.httpClient.getAllWorkspaces,
        "SET_WORKSPACES",
        commit
      );

      // get schema
      api.emit("schema_read", (resp) => {
        commit("SET_SCHEMA", resp);
        commit("SET_READY", true);
      });
    },
    async reload({ dispatch }) {
      dispatch("load");
    },
    async onOrgReload({ dispatch }) {
      await dispatch("api/reloadDb", null, { root: true });
      dispatch("reload");
    },
    async pushNotification({ commit }, message) {
      commit("SET_PUSH_NOTIFICATION", message);
    },
  },
};
