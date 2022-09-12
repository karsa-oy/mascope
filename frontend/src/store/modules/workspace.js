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
            rootState.api.emit('subscribe', workspace.workspace_id);
            // reload sample batches
            const batches = await rootState.api.query(`--sql
                SELECT * FROM sample_batch
                WHERE workspace_id == '${workspace.workspace_id}';
            `);
            await commit('SET_BATCHES', batches);
            await commit('SET_ACTIVE', workspace);
        },
        async unload({ rootState, commit, dispatch }) {
            if (!state.active) return;
            rootState.api.emit('unsubscribe', state.active.workspace_id);
            commit('SET_ACTIVE', null);
            commit('SET_BATCHES', []);
            dispatch("batch/unload", null, {root:true})
        },
        async onWorkspaceReload({ state, dispatch }) {
            await dispatch('api/reloadDb', null, {root:true});
            dispatch('load', state.active);
        }
    }
}