
export default {
    namespaced: true,
    state: {
        rows: [],
        $rooms: [],
        $listRequest: null,
        $listResponse: null,
        $save: null,
        $delete: null,
    },
    mutations: {
        SET_ROWS(state, rows) {
            state.rows = rows;
        },
        GET_ROWS(state, requestObject) {
            state.$listRequest = requestObject;
        },
        SAVE(state, template) {
            state.$save = {
                ...template,
            }
        },
        DELETE(state, id) {
            state.$delete = {
                id: id,
            }
        },
    },
    actions: {
        requestTemplates({ commit }, requestObject) {
            commit('GET_ROWS', requestObject);
        },
        handleResponse({ state, commit }) {
            console.log("teplate handleResponse", state.$listResponse);
            commit('SET_ROWS', state.$listResponse);
        },
        save({ commit }, template) {
            commit('SAVE', template);
        },
        delete({ commit }, id) {
            commit('DELETE', id);
        },
    },
    watchers: {
        'template/$listResponse': 'template/handleResponse',
    }
}
