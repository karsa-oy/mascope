import selection from "./selection"
import { createTableModule } from "$lib/store";

export default createTableModule({
    namespace: 'sample_batch',
    getters: {
        status: (state, getters, rootState) =>
            (row) => {
                let selectedRow = rootState
                    .sample.batch.selection.row
                let selected = selectedRow
                    ? selectedRow.id == row.id
                    : false;
                let full = rootState
                    .sample.batch.selection.full;
                if (!selected && !full) {
                    return 'not-selected';
                } else if (selected && !full) {
                    return 'partially-selected';
                } else if (selected && full) {
                    return 'fully-selected';
                } else {
                    console.warn(`Sample batch selection in a bad state;`, {
                        selected,
                        full
                    });
                }
            }
    },
    actions: {
        async workspaceSelected({ dispatch, state, rootState }) {
            if (!rootState.workspace.active) {
                state.rows = [];
                return;
            }
            await dispatch(
                'read', { workspaceId: rootState.workspace.active.id });
        },
    },
    modules: {
        selection
    },
    watchers: {
        'workspace/active': 'sample/batch/workspaceSelected',
    }
});