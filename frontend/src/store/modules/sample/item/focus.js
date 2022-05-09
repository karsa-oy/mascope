export default {
    namespaced: true,
    state: {
        row: null
    },
    mutations: {
        SET(state, { item }) {
            state.row = item;
        },
        RESET(state) {
            state.row = null;
        }
    },
    actions: {
        async toggle({ commit, getters }, item) {
            let focused = getters['active'](item);
            if (!focused) {
                await commit('SET', { item });
            } else {
                await commit('RESET');
            }
        },
        sync({ state, commit, getters }) {
            let rowInFocus = state.row;
            let rowNotSelected = !getters['selected'];
            if (rowInFocus && rowNotSelected) {
                commit('RESET')
            }
        }
    },
    getters: {
        active: (state) =>
            (item) => state.row ? state.row == item : false,
        // check if focus item is selected
        selected: (state, getters, rootState, rootGetters) =>
            state.row
                ? rootGetters['sample/item/selection/active'](state.row)
                : false
    },
    watchers: {
        'sample/item/focus/selected': 'sample/item/focus/sync'
    }
}