import { createTableModule } from "$lib/store";
import table from "$lib/table";

export default createTableModule({
    namespace: 'workspace',
    state: {
        // state
        active: null,
        // API
        $room: 'workspaces',
        $roomActive: null,
    },
    mutations: {
        SET(state, { workspace }) {
            state.active = workspace;
            state.$roomActive = [workspace.id];
        },
        RESET(state) {
            state.active = null
        }
    },
    actions: {
        sync({ state, getters, commit }) {
            let workspaceId = getters['queryString'];
            if (workspaceId) {
                let workspace = table.get(state.rows, { id: workspaceId });
                commit('SET', { workspace });
            } else {
                commit('RESET');
            }
        }
    },
    getters: {
        queryString(state, getters, rootState) {
            return rootState.query ? rootState.query.w : null;
        }
    },
    watchers: {
        "workspace/queryString": "workspace/sync"
    }
})