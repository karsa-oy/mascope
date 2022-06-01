export default {
    namespaced: true,
    state: {
        row: null,
        $request: null,
        $response: null
    },
    mutations: {
        GET_SCHEMA(state, requestObject) {
            state.$request = requestObject;
        },
        SET_SCHEMA(state, schema) {
            state.row = schema;
        }
    },
    actions: {
        handleResponse: function({ state, commit }) {
            commit('SET_SCHEMA', state.$response.schema);
        },
        requestSchema: function({ commit }) {
            commit('GET_SCHEMA', {});
        },
    },
    watchers: {
        'sample/file/schema/$response': 'sample/file/schema/handleResponse',
    }
}