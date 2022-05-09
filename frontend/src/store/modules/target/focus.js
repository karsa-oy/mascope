export default {
    namespaced: true,
    state: {
        row: null,
        level: null
    },
    mutations: {
        SET(state, { target, level }) {
            state.row = target;
            state.level = level;
        },
        RESET(state) {
            state.row = null;
            state.level = null;
        }
    },
    actions: {
        async toggle({ commit, getters }, { target, level }) {
            let focused = getters['active'](target);
            if (!focused) {
                await commit('SET', { target, level });
            } else {
                await commit('RESET');
            }
        },
        sync({ state, commit, getters }) {
            let rowInFocus = state.row;
            let rowNotSelected = getters['selected'];
            if (rowInFocus && rowNotSelected) {
                commit('RESET');
            }
        }
    },
    getters: {
        active: (state) =>
            (target) => state.row ? state.row.id == target.id : false,
        selected: (state) =>
            state.row ? state.row._selected != 'none' : false
    }
}