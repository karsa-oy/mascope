export default {
    namespaced: true,
    state: {
        rows: []
    },
    mutations: {
        SET(state, { items }) {
            let itemNotSelected =
                (item) => !state.rows
                    .map(row => row.id)
                    .includes(item.id)
            let unselectedItems =
                items.filter(itemNotSelected)
            state.rows
                .push(...unselectedItems);
        },
        UNSET(state, { items }) {
            let itemIds = items.map(item => item.id);
            state.rows = state.rows
                .filter(row => !itemIds.includes(row.id));
        },
        RESET(state) {
            state.rows = [];
        }
    },
    actions: {
        async toggle({ commit, getters }, item) {
            let items = [item]
            let selected = getters['active'](item);
            if (!selected) {
                commit('SET', { items });
            } else {
                commit('UNSET', { items });
            }
        },
        sync({ commit, rootState }) {
            commit('RESET');
            let items = rootState.sample.item.rows;
            if (items) {
                commit('SET', { items });
            }
        }
    },
    getters: {
        active: (state) =>
            (...items) => items.every(
                item => state.rows
                    .map(row => row.id)
                    .includes(item.id)
            ),
    },
    watchers: {
        'sample/item/rows': 'sample/item/selection/sync'
    }
}