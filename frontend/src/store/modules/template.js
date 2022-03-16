
export default {
    namespaced: true,
    state: {
        $rooms: [],
        $response: null,
        $listRequest: null,
        $listResponse: null,
        $save: null,
        $delete: null,
    },
    mutations: {
        listRequest(state) {
            state.$listRequest = {};
        },
        save(state, template) {
            state.$save = {
                ...template,
            }
        },
        delete(state, id) {
            state.$delete = {
                id: id,
            }
        },
    },
    actions: {
        listRequest(context) {
            context.commit('listRequest', {})
        },
        save(context, template) {
            context.commit('save', template)
        },
        delete(context, id) {
            context.commit('delete', id)
        },
    },
    getters: {},
}
