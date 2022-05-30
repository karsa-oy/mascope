import schema from "./schema";

export default {
    namespaced: true,
    modules: {
        schema
    },
    state: {
        rows: [],
        $listRequest: null,
        $listResponse: null,
        $updateRequest: null,
    },
    mutations: {
        GET_ROWS(state, filters) {
            console.log(filters);
            state.$listRequest = filters;
        },
        SET_ROWS(state, fileList) {
            state.rows = fileList;
        },
        UPDATE(state, row) {
            state.$updateRequest = { ...row, id: row.id || row.filename };
        },
    },
    actions: {
        handleListResponse: function({ state, commit }) {
            let response = state.$listResponse;
            commit('SET_ROWS', response.records);
        },
        listFiles: function({ commit }, { filters }) {
            commit('GET_ROWS', filters);
        }
    },
    watchers: {
        'sample/file/$listResponse': 'sample/file/handleListResponse',
    }
}