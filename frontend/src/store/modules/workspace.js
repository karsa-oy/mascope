import { make } from 'vuex-pathify';

const state = {
    active: null,
    batches: [],
}

export default {
    namespaced: true,
    state,
    mutations: make.mutations(state),
    actions: {
        async load({ commit, rootState }, workspace) {
            const dbcon = rootState.api.dbcon;
            // reload sample batches
            const batches = await dbcon.query(`--sql
                SELECT * FROM sample_batch
                WHERE workspace_id == '${workspace.workspace_id}';
            `);
            await commit('SET_BATCHES', batches.toArray());
            await commit('SET_ACTIVE', workspace);
        },
        async unload({ commit }) {
            commit('SET_ACTIVE', null);
            commit('SET_BATCHES', []);
        },
        async onWorkspaceReload({ state, dispatch }, workspaceId) {
            if (state.active.workspace_id == workspaceId) {
                dispatch('load', workspaceId);
            }
        }
    }
}