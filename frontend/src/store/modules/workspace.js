import table from "$lib/table";

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
        $createRequest: null,
        $updateRequest: null,
        $deleteRequest: null,
        $room: 'workspaces',
        $roomActive: [],
        $endpoint: 'workspace_rows'
    },
    mutations: {
        create(state, workspace) {
            state.$createRequest = {
                id: workspace.id ? workspace.id : table.genId(),
                name: workspace.name,
                description: workspace.description,
            }
        },
        update(state, workspace) {
            state.$updateRequest = {
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
}