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
        paramPeakMinIntensity: 1,
        paramPeakMinSeparation: 3,
        paramMzRange: null,
        paramTRange: null,
        // API
        $rooms: [],
        $response: null,
        $batchListRequest: null,
        $batchCreateRequest: null,
        $batchUpdateRequest: null,
        $batchDeleteRequest: null,
        $itemListRequest: null,
        $itemCreateRequest: null,
        $itemUpdateRequest: null,
        $itemDeleteRequest: null,
        $peakListRequest: null,
    },
    mutations: {
        // Batch
        batchList(state, workspace) {
            state.$batchListRequest = {
                requestId: table.genId(),
                workspaceId: workspace.id
            }
        },
        batchCreate(state, batch) {
            state.$batchCreateRequest = {
                requestId: table.genId(),
                id: batch.id ? batch.id : table.genId(),
                name: batch.name,
                description: batch.description,
                workspaceId: batch.workspaceId
            };
        },
        batchUpdate(state, batch) {
            state.$batchUpdateRequest = {
                requestId: table.genId(),
                ...batch
            };
        },
        batchDelete(state, batch) {
            state.$batchDeleteRequest = {
                requestId: table.genId(),
                ...batch
            };
        },
        batchFollow(state, batch) {
            state.$rooms.push(batch.id);
        },
        batchUnfollow(state, batch) {
            state.$rooms = state.$rooms.filter((r) => (r !== batch.id));
        },
        batchOpen(state, batch) {
            table.update(state.batchRows,
                { id: batch.id, _open: true },
                { partial: true }
            );
        },
        batchClose(state, batch) {
            table.update(state.batchRows,
                { id: batch.id, _open: false },
                { partial: true }
            );
        },
        batchHandleResponse(state, { rows, filters }) {
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
        batchPeaksClear(state, batch) {
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
        itemList(state, batch) {
            state.$itemListRequest = {
                requestId: table.genId(),
                ...batch
            }
        },
        itemClear(state, batch) {
            state.itemRows = table
                .remove(state.itemRows, { batchId: batch.id });
        },
        itemReplace(state, { rows, filters, selected }) {
            state.itemRows = table
                .remove(state.itemRows, filters);
            state.itemRows
                .push(...rows.map(row => ({ ...row, _selected: selected })));
        },
        itemPeakClear(state, item) {
            table.update(state.itemRows,
                { id: item.id, peaks: null }
            );
        },
        // Peak
        itemPeakList(state, { sampleItemId, filename, parameters }) {
            state.$peakListRequest = {
                requestId: table.genId(),
                sampleItemId,
                filename,
                ...parameters
            }
        },
        peakListHandleResponse(state, {
            sampleItemId,
            mzsBytes,
            heightsBytes,
            tofsBytes
        }) {
            let sampleRow = table.get(state.itemRows, { id: sampleItemId });
            let mzCol = new Float32Array(mzsBytes);
            let heightCol = new Float32Array(heightsBytes);
            let tofCol = new Float32Array(tofsBytes);
            sampleRow.peaks = { mzCol, heightCol, tofCol };
        },
        // selection
        selectionSet(state, { level, ids, selected }) {
            let levelRows = level + 'Rows';
            for (let id of ids) {
                table.update(state[levelRows],
                    { id, _selected: selected },
                    { partial: true }
                );
            }
        },
        activationSet(state, { batch, active }) {
            let row = table.get(state.batchRows, { id: batch.id });
            row._active = active;
        }
    },
    actions: {
        // requests
        batchList({ commit, rootState }) {
            commit('batchList', rootState.workspace.active)
        },
        async itemPeakList({ commit, state }, {
            item,
            mzRange = state.paramMzRange,
            tRange = state.paramTRange,
            minPeakIntensity = state.paramPeakMinIntensity,
            minPeakSeparation = state.paramPeakMinSeparation,
            minPeakWidth = state.paramPeakMinWidth
        }) {
            commit('itemPeakList', {
                sampleItemId: item.id,
                filename: item.filename,
                parameters: {
                    mzRange,
                    tRange,
                    minPeakIntensity,
                    minPeakSeparation,
                    minPeakWidth
                }
            });
        },
        async batchPeakList({ dispatch, state }, batch) {
            let batchItems = table.select(state.itemRows, { batchId: batch.id });
            for (let item of batchItems) {
                await dispatch('itemPeakList', { item });
            }
        },
        async peakListMissing({ dispatch, state }) {
            let peakRequestConditions = {
                _selected: 'all',
                peaks: null
            }
            let itemsRequiringPeaks = table
                .select(state.itemRows, peakRequestConditions);
            for (let item of itemsRequiringPeaks) {
                await dispatch('itemPeakList', { item });
            }
        },
        // responses
        handleResponse({ state, commit, dispatch }) {
            if (state.$response.type == 'peak-list') {
                commit('peakListHandleResponse', state.$response.payload)
                let sampleItem = table.get(state.itemRows, {
                    id: state.$response.payload.sampleItemId
                });
                dispatch('match/request', {
                    sampleItem
                }, { root: true });
            } else {
                let { level, filters, rows } = state.$response.payload;
                if (level == 'batch') {
                    commit('batchHandleResponse', { rows, filters });
                } else if (level == 'item') {
                    dispatch('itemHandleResponse', { rows, filters })
                } else {
                    throw Error('Undefined sample row level in update');
                }
            }
        },
        async itemHandleResponse({ state, commit, dispatch }, { rows, filters }) {
            if (rows.length > 0) {
                // use the first row to infer batch
                let firstRow = rows[0];
                let batch = table.get(state.batchRows, { id: firstRow.batchId });
                // set selected status based on batch selection
                let mapSelection = { all: 'all', some: 'none', none: 'none' };
                let selected = mapSelection[batch._selected];
                await commit('itemReplace', { rows, filters, selected });
                dispatch('peakListMissing');
            } else {
                console.log("Handled item response but no data was returned.")
            }
        },
        // selection
        async batchSelectionToggle({ state, commit, dispatch }, batch) {
            let batchWasActive = batch._active;
            let batchWasOpen = batch._open;
            let action = batch._selected == 'all' ? 'unselect' : 'select';
            if (action == 'select') {
                await dispatch('batchActivate', batch);
                await commit('selectionSet', {
                    level: 'batch',
                    ids: [batch.id],
                    selected: 'all'
                });
                if (batchWasActive) {
                    let batchItemIds = table
                        .select(state.itemRows, { batchId: batch.id })
                        .map(item => item.id);
                    await commit('selectionSet', {
                        level: 'item',
                        ids: batchItemIds,
                        selected: 'all'
                    });
                    dispatch('peakListMissing');
                }
            } else if (action == 'unselect') {
                await commit('selectionSet', {
                    level: 'batch',
                    ids: [batch.id],
                    selected: 'none'
                });
                if (batchWasOpen) {
                    let batchItemIds = table
                        .select(state.itemRows, { batchId: batch.id })
                        .map(item => item.id);
                    await commit('selectionSet', {
                        level: 'item',
                        ids: batchItemIds,
                        selected: 'none'
                    });
                    dispatch('batchMatchClear', batch);
                    commit('batchPeaksClear', batch);
                }
                await dispatch('batchDeactivate', batch);
            } else {
                throw Error('Sample batch selection in a bad state.');
            }
        },
        async itemSelectionToggle({ state, commit, dispatch }, item) {
            let selected = selection.propegateDown(item);
            commit('selectionSet', {
                level: 'item',
                ids: [item.id],
                selected
            });
            if (selected == 'all') {
                await dispatch(
                    'itemPeakList', { item }
                );
            } else if (selected == 'none') {
                await dispatch(
                    'match/removeBySampleItem', item,
                    { root: true }
                );
                await commit('itemPeakClear', item);
            }
            // propegate batch selection state
            let batchItems = table
                .select(state.itemRows, { batchId: item.batchId });
            commit('selectionSet', {
                level: 'batch',
                ids: [item.batchId],
                selected: selection.propegateUp(batchItems)
            });
        },
        // activation - fetching data and subscribing to backend updates
        batchActivate({ commit }, batch) {
            // only unactive batches can be activated
            if (!batch._active) {
                commit('itemList', batch);
                commit('batchFollow', batch);
                commit('activationSet', { batch, active: true });
            }
        },
        batchDeactivate({ commit, dispatch }, batch) {
            // open and selected batches can't be deactivated
            if (batch._selected == 'none' && !batch._open) {
                dispatch('batchMatchClear', batch);
                commit('itemClear', batch);
                commit('batchUnfollow', batch);
                commit('activationSet', { batch, active: false });
            }
        },
        // opening - expanding in the sample browser
        batchOpen({ commit, dispatch }, batch) {
            if (!batch._open) {
                commit('batchOpen', batch);
                dispatch('batchActivate', batch);
            }
        },
        batchClose({ commit, dispatch }, batch) {
            if (batch._open) {
                commit('batchClose', batch);
                dispatch('batchDeactivate', batch);
            }
        },
        // helpers
        batchMatchClear({ state, dispatch }, batch) {
            let batchItems = table
                .select(state.itemRows, { batchId: batch.id });
            for (let item of batchItems) {
                dispatch(
                    'match/removeBySampleItem', item,
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
                    { matches: rootGetters['match/ratings']({ level, selected }) }
                );
            },
    }
}