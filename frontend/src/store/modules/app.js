import { make } from 'vuex-pathify';

const state = {
    workspaces: [],
    targetCollections: [],
    attributeTemplates: [],
    ionMechanisms: [],
    schema: {},
    ready: false,
}
export default {
    namespaced: true,
    state,
    mutations: make.mutations(state),
    actions: {
        async load({ commit, rootState }) {
            const api = rootState.api;
            // reload workspaces
            const workspaces = await api.query(`--sql
                SELECT * FROM workspace;
            `);
            commit('SET_WORKSPACES', workspaces);
            // reload target collections
            const collections = await api.query(`--sql
                SELECT * FROM target_collection;
            `);
            commit('SET_TARGET_COLLECTIONS', collections);
            // reload attribute templates
            const attributeTemplates = await api.query(`--sql
                SELECT * FROM attribute_template;
            `);
            commit('SET_ATTRIBUTE_TEMPLATES', attributeTemplates);
            // reload ionization mechanisms
            const ionMechanisms = await api.query(`--sql
                SELECT * FROM config_mechanism;
            `);
            commit('SET_ION_MECHANISMS', ionMechanisms);
            api.emit('schema_read', (resp) => {
                commit('SET_SCHEMA', resp);
                commit('SET_READY', true);
            });
        },
        async reload({ dispatch }) {
            dispatch('load');
        },
        async onOrgReload({ dispatch }) {
            dispatch('reload');
        }
    }
}