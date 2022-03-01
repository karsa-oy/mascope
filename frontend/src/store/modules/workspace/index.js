import table from "$lib/table";

import target from "./target";
import sample from "./sample";
import match from "./match";

export default {
    namespaced: true,
    state: {
        // meta
        cols: [],
        // data
        $rows: [],
        // state
        active: null,
        // API
        $saveRequest: null,
        $deleteRequest: null,
        $room: 'workspaces',
        $endpoint: 'workspace_rows'
    },
    mutations: {
        save(state, workspace) {
            state.$saveRequest = {
                id: workspace.id ? workspace.id : table.genId(),
                name: workspace.name,
                description: workspace.description,
            }
        },
        delete(state, workspace) {
            state.$deleteRequest = workspace;
        }
    },
    getters: {
        byId: (state) => (id) => {
            return table.get(state.$rows, { id });
        }
    },
    modules: {
        target,
        sample,
        match,
    },
}