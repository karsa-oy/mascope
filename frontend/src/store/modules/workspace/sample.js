import table from '$lib/table';
import selection from '$lib/selection';

export default {
    namespaced: true,
    state: {
        // meta
        cols: [
            { field: 'workspaceId', label: 'Workspace ID' },
            { field: 'batchId', label: 'Batch ID' },
            { field: 'filename', label: 'Filename' }
        ],
        // data
        batchRows: [],
        itemRows: [],
        // Parameters
        paramPeakMinIntensity: 5,
        paramPeakMinSeperation: 3,
        paramPeakMinWidth: 3,
        paramMzRange: null,
        paramTRange: null,
        // API
        $rooms: [],
        $update: null,
        $batchFetchRequest: null,
        $batchSaveRequest: null,
        $batchDeleteRequest: null,
        $itemFetchRequest: null,
        $itemSaveRequest: null,
        $itemDeleteRequest: null,
        $peakRequest: null,
    },
    mutations: {
        // Batch
        requestBatches(state, workspace) {
            state.$batchFetchRequest = {
                requestId: table.genId(),
                ...workspace
            }
        },
        followBatch(state, batch) {
            let room = batch.workspaceId + batch.id;
            state.$rooms.push(room);
        },
        unfollowBatch(state, batch) {
            let room = batch.workspaceId + batch.id;
            state.$rooms = state.$rooms.filter((r) => (r !== room));
        },
        setBatchOpen(state, batch) {
            table.update(state.batchRows,
                { id: batch.id, _open: true },
                { partial: true }
            );
        },
        setBatchClosed(state, batch) {
            table.update(state.batchRows,
                { id: batch.id, _open: false },
                { partial: true }
            );
        },
        handleBatchUpdate(state, { rows, filters }) {
            let extras = {
                _selected: 'none',
                _open: false,
                _active: false
            };
            state.batchRows = table
                .remove(state.batchRows, filters);
            state.batchRows
                .push(...rows.map(row => ({ ...row, ...extras })));
        },
        removeBatchPeaks(state, batch) {
            let ids = table
                .select(state.itemRows, { batchId: batch.id })
                .map(row => row.id);
            for (let id of ids) {
                table.update(state.itemRows,
                    { id, peaks: null }
                );
            }
        },
        // Item
        requestItems(state, batch) {
            state.$itemFetchRequest = {
                requestId: table.genId(),
                ...batch
            }
        },
        clearItems(state, batch) {
            state.itemRows = table
                .remove(state.itemRows, { batchId: batch.id });
        },
        replaceItemRows(state, { rows, filters, selected }) {
            state.itemRows = table
                .remove(state.itemRows, filters);
            state.itemRows
                .push(...rows.map(row => ({ ...row, _selected: selected })));
        },
        removeItemPeaks(state, item) {
            table.update(state.itemRows,
                { id: item.id, peaks: null }
            );
        },
        // Peak
        requestPeaks(state, { sampleItemId, filename, parameters }) {
            state.$peakRequest = {
                requestId: table.genId(),
                sampleItemId,
                filename,
                ...parameters
            }
        },
        handlePeakUpdate(state, { sampleItemId, mzsBytes, heightsBytes, tofsBytes }) {
            let sampleRow = table.get(state.itemRows, { id: sampleItemId });
            let mzCol = new Float32Array(mzsBytes);
            let heightCol = new Float32Array(heightsBytes);
            let tofCol = new Float32Array(tofsBytes);
            sampleRow.peaks = { mzCol, heightCol, tofCol };
        },
        // selection
        setSelection(state, { level, ids, selected }) {
            let levelRows = level + 'Rows';
            for (let id of ids) {
                table.update(state[levelRows],
                    { id, _selected: selected },
                    { partial: true }
                );
            }
        },
        setActivation(state, { batch, active }) {
            let row = table.get(state.batchRows, { id: batch.id });
            row._active = active;
        }
    },
    actions: {
        // requests
        requestBatches({ commit, rootState }) {
            commit('requestBatches', rootState.workspace.active)
        },
        async requestItemPeaks({ commit, state }, {
            item,
            mzRange = state.paramMzRange,
            tRange = state.paramTRange,
            minPeakIntensity = state.paramPeakMinIntensity,
            minPeakSeperation = state.paramPeakMinSeperation,
            minPeakWidth = state.paramPeakMinWidth
        }) {
            commit('requestPeaks', {
                sampleItemId: item.id,
                filename: item.filename,
                parameters: {
                    mzRange,
                    tRange,
                    minPeakIntensity,
                    minPeakSeperation,
                    minPeakWidth
                }
            });
        },
        async requestBatchPeaks({ dispatch, state }, batch) {
            let batchItems = table.select(state.itemRows, { batchId: batch.id });
            for (let item of batchItems) {
                await dispatch('requestItemPeaks', { item });
            }
        },
        async requestNeededPeaks({ dispatch, state }) {
            let peakRequestConditions = {
                _selected: 'all',
                peaks: null
            }
            let itemsRequiringPeaks = table
                .select(state.itemRows, peakRequestConditions);
            for (let item of itemsRequiringPeaks) {
                await dispatch('requestItemPeaks', { item });
            }
        },
        // responses
        handleUpdate({ state, commit, dispatch }) {
            if (state.$update.type == 'peak-fetch') {
                commit('handlePeakUpdate', state.$update.payload)
                let sampleItem = table.get(state.itemRows, {
                    id: state.$update.payload.sampleItemId
                });
                dispatch('workspace/match/request', {
                    sampleItem
                }, { root: true });
            } else {
                let { level, filters, rows } = state.$update.payload;
                if (level == 'batch') {
                    commit('handleBatchUpdate', { rows, filters });
                } else if (level == 'item') {
                    dispatch('handleItemUpdate', { rows, filters })
                } else {
                    throw Error('Undefined sample row level in update');
                }
            }
        },
        async handleItemUpdate({ state, commit, dispatch }, { rows, filters }) {
            // use the first row to infer batch
            let firstRow = rows[0];
            let batch = table.get(state.batchRows, { id: firstRow.batchId });
            // set selected status based on batch selection
            let mapSelection = { all: 'all', some: 'none', none: 'none' };
            let selected = mapSelection[batch._selected];
            await commit('replaceItemRows', { rows, filters, selected });
            dispatch('requestNeededPeaks');
        },
        // selection
        async batchToggleSelection({ state, commit, dispatch }, batch) {
            let batchWasActive = batch._active;
            let batchWasOpen = batch._open;
            let action = batch._selected == 'all' ? 'unselect' : 'select';
            if (action == 'select') {
                await dispatch('activateBatch', batch);
                await commit('setSelection', {
                    level: 'batch',
                    ids: [batch.id],
                    selected: 'all'
                });
                if (batchWasActive) {
                    let batchItemIds = table
                        .select(state.itemRows, { batchId: batch.id })
                        .map(item => item.id);
                    await commit('setSelection', {
                        level: 'item',
                        ids: batchItemIds,
                        selected: 'all'
                    });
                    dispatch('requestNeededPeaks');
                }
            } else if (action == 'unselect') {
                await commit('setSelection', {
                    level: 'batch',
                    ids: [batch.id],
                    selected: 'none'
                });
                if (batchWasOpen) {
                    let batchItemIds = table
                        .select(state.itemRows, { batchId: batch.id })
                        .map(item => item.id);
                    await commit('setSelection', {
                        level: 'item',
                        ids: batchItemIds,
                        selected: 'none'
                    });
                    dispatch('removeBatchMatches', batch);
                    commit('removeBatchPeaks', batch);
                }
                await dispatch('deactivateBatch', batch);
            } else {
                throw Error('Sample batch selection in a bad state.');
            }
        },
        async itemToggleSelection({ state, commit, dispatch }, item) {
            let selected = selection.propegateDown(item);
            commit('setSelection', {
                level: 'item',
                ids: [item.id],
                selected
            });
            if (selected == 'all') {
                await dispatch(
                    'requestItemPeaks', { item }
                );
            } else if (selected == 'none') {
                await dispatch(
                    'workspace/match/removeBySampleItem', item,
                    { root: true }
                );
                await commit('removeItemPeaks', item);
            }
            // propegate batch selection state
            let batchItems = table
                .select(state.itemRows, { batchId: item.batchId });
            commit('setSelection', {
                level: 'batch',
                ids: [item.batchId],
                selected: selection.propegateUp(batchItems)
            });
        },
        // activation - fetching data and subscribing to backend updates
        activateBatch({ commit }, batch) {
            // only unactive batches can be activated
            if (!batch._active) {
                commit('requestItems', batch);
                commit('followBatch', batch);
                commit('setActivation', { batch, active: true });
            }
        },
        deactivateBatch({ commit, dispatch }, batch) {
            // open and selected batches can't be deactivated
            if (batch._selected == 'none' && !batch._open) {
                dispatch('removeBatchMatches', batch);
                commit('clearItems', batch);
                commit('unfollowBatch', batch);
                commit('setActivation', { batch, active: false });
            }
        },
        // opening - expanding in the sample browser
        openBatch({ commit, dispatch }, batch) {
            if (!batch._open) {
                commit('setBatchOpen', batch);
                dispatch('activateBatch', batch);
            }
        },
        closeBatch({ commit, dispatch }, batch) {
            if (batch._open) {
                commit('setBatchClosed', batch);
                dispatch('deactivateBatch', batch);
            }
        },
        // helpers
        removeBatchMatches({ state, dispatch }, batch) {
            let batchItems = table
                .select(state.itemRows, { batchId: batch.id });
            for (let item of batchItems) {
                dispatch(
                    'workspace/match/removeBySampleItem', item,
                    { root: true }
                );
            }
        }
    },
    getters: {
        itemStats: (state, getters, rootState, rootGetters) =>
            ({ level = 'compound', selected = true }) => {
                return table.query(
                    `
                    select
                        m.sampleItemId as id
                        ,m.rating
                        ,first(m.sampleFilename) as filename
                        ,count(*) as matchCount
                        ,count(distinct m.target${level}Id) as target${level}Count
                    from matches m
                    group by m.sampleItemId, m.rating
               `,
                    { matches: rootGetters['workspace/match/ratings']({ level, selected }) }
                );
            },
    }
}