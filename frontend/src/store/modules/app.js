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
            commit('SET_WORKSPACES', workspaces.toArray());
            // reload target collections
            const collections = await api.query(`--sql
                SELECT * FROM target_collection;
            `);
            commit('SET_TARGET_COLLECTIONS', collections.toArray());
            // reload attribute templates
            const attributeTemplates = await api.query(`--sql
                SELECT * FROM attribute_template;
            `);
            commit('SET_ATTRIBUTE_TEMPLATES', attributeTemplates.toArray());
            // reload ionization mechanisms
            const ionMechanisms = await api.query(`--sql
                SELECT * FROM config_mechanism;
            `);
            commit('SET_ION_MECHANISMS', ionMechanisms.toArray());
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