export default {
    namespaced: true,
    state: {
        row: null,
        $room: null,
        full: null
    },
    mutations: {
        SET(state, { batch, full }) {
            state.row = batch;
            state.$room = batch ? batch.id : null;
            state.full = full;
        },
        RESET(state, { batch }) {
            if (state.row != batch) {
                throw Error('Trying to deselect an unselected batch.')
            } else {
                state.row = null
                state.$room = null;
                state.full = null;
            }
        },
    },
    actions: {
        async toggle({ commit, dispatch, getters }, batch) {
            let selected = getters['active'](batch);
            if (!selected) {
                await commit('SET', { batch, full: true });
                await dispatch(
                    'sample/item/read', { batchId: batch.id },
                    { root: true }
                );
            } else {
                await commit('RESET', { batch });
                await dispatch(
                    'sample/item/clear', { batchId: batch.id },
                    { root: true }
                );
            }
        },
        sync({ commit, state, getters }) {
            commit('SET', {
                batch: state.row,
                full: getters['full']
            })
        }
    },
    getters: {
        active: (state) =>
            (batch) => state.row
                ? state.row.id == batch.id
                : false,
        full: (state, getters, rootState) => {
            let batchSelected = state.row;
            if (batchSelected) {
                let itemInBatch =
                    (row) => row.batchId == batchSelected.id
                let selectedCount = rootState
                    .sample.item.selection.rows
                    .filter(itemInBatch)
                    .length
                let totalCount = rootState
                    .sample.item.rows
                    .filter(itemInBatch)
                    .length
                return selectedCount == totalCount;
            } else {
                return null;
            }
        }
    },
    watchers: {
        'sample/batch/selection/full': 'sample/batch/selection/sync'
    }
}