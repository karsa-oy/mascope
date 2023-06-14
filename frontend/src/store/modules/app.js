import { make } from "vuex-pathify";
// import httpClient from "../../httpClient.js";

const mode = import.meta.env.MASCOPE_PUBLIC_MODE;

const state = {
  attributeTemplates: [],
  instruments: [],
  ionMechanisms: [],
  mode: mode,
  pushNotification: null,
  ready: false,
  schema: {},
  targetCollections: [],
  workspaces: [],
};
export default {
  namespaced: true,
  state,
  mutations: make.mutations(state),
  actions: {
    async load({ commit, rootState }) {
      const api = rootState.api;
      // load attribute templates
      const attributeTemplates = await api.query(`--sql
                SELECT * FROM attribute_template;
            `);
      commit("SET_ATTRIBUTE_TEMPLATES", attributeTemplates);
      // load target collections
      const collections = await api.query(`--sql
                SELECT * FROM target_collection;
            `);
      commit("SET_TARGET_COLLECTIONS", collections);
      // load instruments
      const instruments = await api.query(`--sql
                SELECT DISTINCT instrument
                FROM instrument_function;
            `);
      commit("SET_INSTRUMENTS", instruments);
      // load ionization mechanisms
      const ionMechanisms = await api.query(`--sql
                SELECT * FROM ionization_mechanism;
            `);
      commit("SET_ION_MECHANISMS", ionMechanisms);
      // load workspaces
      const response = await api.httpClient.getAllWorkspaces();
      const workspaces = response.data.data;
      commit("SET_WORKSPACES", workspaces);

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
