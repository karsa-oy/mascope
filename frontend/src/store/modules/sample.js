import table from '$lib/table';
import selection from '$lib/selection';
import { toTitleCase } from '$lib/string';

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
        fileSchema: {},
        itemSchema: {},
        // API
        $rooms: [],
        $response: null,
        $batchListRequest: null,
        $batchCreateRequest: null,
        $batchUpdateRequest: null,
        $batchDeleteRequest: null,
        $itemListRequest: null,
        $itemCreateRequest: null,
        $itemDeleteRequest: null,
        $peakListRequest: null,
        $fileUpdateRequest: null,
        $itemUpdateRequest: null,
        $fileListRequest: null,
        $fileListResponse: null,
        $fileSchemaRequest: null,
        $fileSchemaResponse: null,
        $itemSchemaRequest: null,
        $itemSchemaResponse: null,
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
        },
        fileUpdate(state, row) {
            // row: {key:value, ...}
            state.$fileUpdateRequest = { ...row, id: row.id || row.filename };
        },
        itemUpdate(state, rows) {
            // rows: [{key:value, ...},...]
            rows.forEach(row => row.id = row.id || table.genId())
            state.$itemUpdateRequest = rows;
        },
        fileListRequest(state, requestObject) {
            state.$fileListRequest = requestObject;
        },
        fileSchemaRequest(state) {
            state.$fileSchemaRequest = {};
        },
        fileSchema(state, schema) {
            state.fileSchema = schema;
        },
        itemSchemaRequest(state) {
            state.$itemSchemaRequest = {};
        },
        itemSchema(state, schema) {
            state.itemSchema = schema;
        },
    },
    actions: {
        // requests
        batchList({ commit, rootState }) {
            commit('batchList', rootState.workspace.active)
        },
        // responses
        handleResponse({ state, commit, dispatch }) {
            let { level, filters, rows } = state.$response.payload;
            if (level == 'batch') {
                commit('batchHandleResponse', { rows, filters });
            } else if (level == 'item') {
                dispatch('itemHandleResponse', { rows, filters })
            } else {
                throw Error('Undefined sample row level in update');
            }
        },
        async itemHandleResponse({ state, commit }, { rows, filters }) {
            if (rows.length > 0) {
                // use the first row to infer batch
                let firstRow = rows[0];
                let batch = table.get(state.batchRows, { id: firstRow.batchId });
                // set selected status based on batch selection
                let mapSelection = { all: 'all', some: 'none', none: 'none' };
                let selected = mapSelection[batch._selected];
                await commit('itemReplace', { rows, filters, selected });
            } else {
                console.log("Handled item response but no data was returned.")
            }
        },
        // selection
        async batchSelectionToggle({ dispatch }, batch) {
            let action = batch._selected == 'all' ? 'unselect' : 'select';
            if (action == 'select') {
                await dispatch('batchUnselectAllBut', batch);
                await dispatch('batchSelect', batch);
            } else if (action == 'unselect') {
                await dispatch('batchUnselect', batch);
            } else {
                throw Error('Sample batch selection in a bad state.');
            }
        },
        async batchSelect({ dispatch, commit, state }, batch) {
            await dispatch('batchActivate', batch);
            await commit('selectionSet', {
                level: 'batch',
                ids: [batch.id],
                selected: 'all'
            });
            let batchItemIds = table
                .select(state.itemRows, { batchId: batch.id })
                .map(item => item.id);
            await commit('selectionSet', {
                level: 'item',
                ids: batchItemIds,
                selected: 'all'
            });
            dispatch('match/request', batch, { root: true });
        },
        async batchUnselect({ dispatch, commit, state }, batch) {
            await dispatch('match/clear', batch, { root: true });
            await commit('selectionSet', {
                level: 'batch',
                ids: [batch.id],
                selected: 'none'
            });
            let batchItemIds = table
                .select(state.itemRows, { batchId: batch.id })
                .map(item => item.id);
            await commit('selectionSet', {
                level: 'item',
                ids: batchItemIds,
                selected: 'none'
            });
            await dispatch('batchDeactivate', batch);
        },
        async batchUnselectAllBut({ state, dispatch }, batch) {
            let fullySelectedBatches = table
                .select(state.batchRows, { _selected: 'all' });
            let partiallySelectedBatches = table
                .select(state.batchRows, { _selected: 'some' });
            let batchesToUnselect = table.remove([
                ...fullySelectedBatches,
                ...partiallySelectedBatches
            ], { id: batch.id });
            for (let batchToUnselect of batchesToUnselect) {
                await dispatch('batchUnselect', batchToUnselect);
            }
        },
        async itemSelectionToggle({ state, commit, dispatch }, item) {
            let selected = selection.propegateDown(item);
            // if selecting
            if (selected == 'all') {
                // deselect all batches except current
                await dispatch('batchUnselectAllBut', { id: item.batchId });
            }
            // set batch selection state
            let batchItems = table
                .select(state.itemRows, { batchId: item.batchId });
            await commit('selectionSet', {
                level: 'batch',
                ids: [item.batchId],
                selected: selection.propegateUp(batchItems)
            });
            // set item selection state
            commit('selectionSet', {
                level: 'item',
                ids: [item.id],
                selected
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
        batchDeactivate({ commit }, batch) {
            // open and selected batches can't be deactivated
            if (batch._selected == 'none' && !batch._open) {
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
    },
    getters: {
        // selected
        selected: (state, getters) =>
            ({ level }) => {
                return getters[level + 'Selected'];
            },
        batchesSelected: function (state) {
            let selected = (row) => ['all', 'some'].includes(row._selected)
            let batchesSelected = state.batchRows.filter(selected);
            return batchesSelected.length > 0 ? batchesSelected : state.batchRows;
        },
        itemsSelected: function (state) {
            let selected = (row) => ['all', 'some'].includes(row._selected)
            let itemsSelected = state.itemRows.filter(selected);
            return itemsSelected.length > 0 ? itemsSelected : state.itemRows;
        },
        // stats
        itemStats: (state, getters, rootState, rootGetters) =>
            ({ level = 'compound', selected = true }) => {
                let targetLevel = 'target' + toTitleCase(level);
                let matchLevel = 'match' + toTitleCase(level);
                let matches = rootGetters['match/ratings']({ level, selected });
                let samples = selected ? getters['itemsSelected'] : state.itemRows;
                let total = table.query(
                    `
                    select
                        m.sampleItemId as id
                        ,count(distinct m.${targetLevel}Id) as ${matchLevel}TotalCount
                    from matches m
                    group by m.sampleItemId
                    `, { matches }
                );
                let probable = table.query(
                    `
                    select
                        m.sampleItemId as id
                        ,count(distinct m.${targetLevel}Id) as ${matchLevel}ProbableCount
                    from matches m
                    where rating = 'probable'
                    group by m.sampleItemId
                    `, { matches }
                );
                let possible = table.query(
                    `
                    select
                        m.sampleItemId as id
                        ,count(distinct m.${targetLevel}Id) as ${matchLevel}PossibleCount
                    from matches m
                    where rating = 'possible'
                    group by m.sampleItemId
                    `, { matches }
                );
                let result = table.query(
                    `
                    select
                        samp.*
                        ,coalesce(tot.${matchLevel}TotalCount, 0) as ${matchLevel}TotalCount
                        ,coalesce(prob.${matchLevel}ProbableCount, 0) as ${matchLevel}ProbableCount
                        ,coalesce(poss.${matchLevel}PossibleCount, 0) as ${matchLevel}PossibleCount
                    from samples samp
                    left join total tot
                        on samp.id = tot.id
                    left join probable prob
                        on samp.id = prob.id
                    left join possible poss
                        on samp.id = poss.id
                    `, { samples, total, probable, possible }
                );
                if (rootState.dev.logGetters) console.table(result);
                return result;
            },
    }
}