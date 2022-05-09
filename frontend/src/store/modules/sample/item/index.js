import selection from "./selection";
import focus from "./focus";
import schema from "./schema";
import stat from "./stat";

import { createTableModule } from "$lib/store";

export default createTableModule({
    namespace: 'sample_item',
    getters: {
        status: (state, getters, rootState) =>
            (row) => {
                let selected = rootState
                    .sample.item.selection.rows
                    .map(item => item.id)
                    .includes(row.id);
                let focusRow = rootState
                    .sample.item.focus.row
                let focused = focusRow
                    ? focusRow.id == row.id
                    : false;
                if (!selected && !focused) {
                    return 'not-selected';
                } else if (selected && !focused) {
                    return 'fully-selected';
                } else if (selected && focused) {
                    return 'focused';
                } else {
                    console.warn(`Sample item selection in a bad state;`, {
                        selected,
                        focused
                    });
                }
            }
    },
    modules: {
        selection,
        focus,
        schema,
        stat
    }
});