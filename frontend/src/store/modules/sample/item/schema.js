export default {
    namespaced: true,
    state: {
        row: null,
        $request: null,
        $response: null
    },
    mutations: {
        HANDLE_RESPONSE(state) {
            state.row = state.$response.schema;
        }
    }
}