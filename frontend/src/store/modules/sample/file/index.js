import schema from "./schema";

export default {
    namespaced: true,
    state: {
        $listRequest: null,
        $listResponse: null,
        $updateRequest: null,
    },
    mutations: {
        UPDATE(state, row) {
            state.$updateRequest = { ...row, id: row.id || row.filename };
        }
    },
    modules: {
        schema
    }
}