import { make } from 'vuex-pathify';

const state = {
    attributeTemplates: [],
    instruments: [],
    ionMechanisms: [],
    ready: false,
    schema: {},
    targetCollections: [],
    workspaces: [],
}
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
            commit('SET_ATTRIBUTE_TEMPLATES', attributeTemplates);
            // load target collections
            const collections = await api.query(`--sql
                SELECT * FROM target_collection;
            `);
            commit('SET_TARGET_COLLECTIONS', collections);
            // load instruments
            const instruments = await api.query(`--sql
                SELECT DISTINCT instrument
                FROM sample_file;
            `);
            commit('SET_INSTRUMENTS', instruments);
            // load ionization mechanisms
            const ionMechanisms = await api.query(`--sql
                SELECT * FROM ionization_mechanism;
            `);
            commit('SET_ION_MECHANISMS', ionMechanisms);
            // load workspaces
            const workspaces = await api.query(`--sql
                SELECT * FROM workspace;
            `);
            commit('SET_WORKSPACES', workspaces);
            // get schema
            api.emit('schema_read', (resp) => {
                commit('SET_SCHEMA', resp);
                commit('SET_READY', true);
            });
        },
        async reload({ dispatch }) {
            dispatch('load');
        },
        async onOrgReload({ dispatch }) {
            await dispatch('api/reloadDb', null, {root:true});
            dispatch('reload');
        }
    }
}