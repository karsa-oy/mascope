import path from "./api/path";

export function bindState(bindings) {
    let computedBindings = Object.keys(bindings)
        .map((localVariable) => {
            let path = bindings[localVariable];
            return {
                [localVariable]: {
                    get() {
                        return this.$store.getters.getPath(path);
                    },
                    set(value) {
                        this.$store.commit('setPath', { path, value })
                    }
                }
            }
        });
    return Object.assign({}, ...computedBindings);
}

export function createTableModule({
    // table specific
    namespace, // own path
    parents = null, // child module paths
    children = null, // parent module paths
    params = null, // store addresses to pass as filters on read
    loadWhen = 'parent-loaded', // 'parents-selected' 'parents-loaded' 'always'
    singleSelect = false,
    focusable = false,
    // standard elements
    state,
    mutations,
    actions,
    getters,
    modules,
    // store plugin
    watchers,
    subs
}) {
    let selectedStatuses = [
        'in-focus',
        'fully-selected',
        'partially-selected'
    ]
    let endpoint = (...args) => path.toSnakeCase(namespace) + '_' + args.join('_')
    return {
        namespaced: true,
        state: () => ({
            rows: [],
            $event: null,
            $room: namespace,
            ...state
        }),
        mutations: {
            TICK(state, { load, change, unload }) {
                // status update propagating down
                if (load.length) {
                    let ids = load.map(row => row.id);
                    // remove outdated rows
                    state.rows = state.rows
                        .filter(row => !ids.includes(row.id));
                    // push new rows
                    state.rows
                        .push(...load);
                }
                if (change.length) {
                    let mapping = change
                        .reduce((i, j) => ({ ...i, ...j }), {});
                    state.rows = state.rows
                        .map(row => row.id in mapping
                            ? { ...row, ...mapping[row.id] }
                            : row
                        )
                }
                if (unload.length) {
                    state.rows = state.rows
                        .filter(row => !unload.includes(row.id));
                }
            },
            TOCK(state, { load, unload, change }) {
                // status update propagating up
                if (load.length) {
                    let ids = load.map(row => row.id);
                    // remove outdated rows
                    state.rows = state.rows
                        .filter(row => !ids.includes(row.id));
                    // push new rows
                    state.rows
                        .push(...load);
                }
                if (change.length) {
                    let mapping = change
                        .reduce((i, j) => ({ ...i, ...j }), {});
                    state.rows = state.rows
                        .map(row => row.id in mapping
                            ? { ...row, ...mapping[row.id] }
                            : row
                        )
                }
                if (unload.length) {
                    state.rows = state.rows
                        .filter(row => !unload.includes(row.id));
                }
            },
            UNLOAD(state) {
                if (loadWhen === 'always') return;
                state.rows = [];
            },
            ...mutations,
        },
        actions: {
            async tick({ commit, dispatch }, { load = [], unload = [], change = [] }) {
                // do nothing if no rows are passed
                let rowCount = load.length + unload.length + change.length;
                if (rowCount == 0) {
                    return;
                }
                if (!children && change) {
                    await dispatch('tock', { load, unload, change })
                } else {
                    // propagate down
                    await commit('TICK', { load, unload, change })
                }
            },
            async tock({ commit }, { load = [], unload = [], change = [] }) {
                // do nothing if no rows are passed
                let rowCount = load.length + unload.length + change.length;
                if (rowCount == 0) {
                    return;
                }
                // propagate up
                commit('TOCK', { load, unload, change });
            },
            async unload({ commit }) {
                commit('UNLOAD');
            },
            // CRUD endpoints
            async create({ rootState }, rows) {
                await rootState.api.call({
                    endpoint: endpoint('create', 'request'),
                }, rows);
            },
            async read({ rootState, dispatch, getters }, filters = {}) {
                console.log(namespace)
                let status = getters['propagateStatusDown'];
                await rootState.api.call({
                    endpoint: endpoint('read', 'request'),
                    onSuccess: (resp) => {
                        let rows = resp.map(row => ({ ...row, ...status(row.id) }));
                        dispatch('tick', { load: rows });
                    }
                }, { ...filters, ...getters['paramFilters'] });
            },
            async update({ rootState }, rows) {
                await rootState.api.call({
                    endpoint: endpoint('update', 'request'),
                }, rows);
            },
            async delete({ rootState }, ids) {
                await rootState.api.call({
                    endpoint: endpoint('delete', 'request'),
                }, ids);
            },
            async clear({ state, dispatch }, filters) {
                let ids = state.rows.filter((row) => {
                    let fullMatch = Object.entries(filters)
                        .every(([field, filter]) => (row[field] == filter))
                    return fullMatch;
                }).map(row => row.id);
                await dispatch('tick', { unload: ids });
            },
            async syncToEvent({ state, dispatch, getters }) {
                let event = state.$event;
                switch (event.type) {
                    case 'create':
                    case 'update': {
                        dispatch('read', {
                            id: event.ids,
                            ...getters['missingFilters']
                        });
                        break;
                    }
                    case 'delete': {
                        dispatch('clear', { id: event.ids });
                        break;
                    }
                }
            },
            async toggle({ dispatch, state, rootState, getters }, row) {
                let toggledRowId = row.id;
                // keyboard shortcuts set operation mode
                let mode;
                if (rootState.key.alt && focusable) {
                    mode = 'focus';
                } else if (rootState.key.control) {
                    mode = 'multiselect'
                } else {
                    mode = 'singleselect'
                }
                // calculate next status 
                let statusMapping = ['singleselect', 'multiselect'].includes(mode)
                    ? {  // if in selection mode:
                        'not-selected': 'fully-selected',
                        'partially-selected': 'fully-selected',
                        'fully-selected': 'not-selected',
                        'in-focus': 'not-selected'
                    } : { // if in focus mode:
                        'not-selected': 'in-focus',
                        'partially-selected': 'in-focus',
                        'fully-selected': 'in-focus',
                        'in-focus': 'fully-selected'
                    }
                let currentStatus = row.status;
                let nextStatus = statusMapping[currentStatus]
                // compute necessary change
                let change;
                switch (mode) {
                    case 'singleselect': {
                        // all rows except toggled unselected
                        change = state.rows
                            .map(row => {
                                let status;
                                if (row.id == toggledRowId) {
                                    if (singleSelect) {
                                        status = nextStatus;
                                    } else {
                                        status = 'fully-selected';
                                    }
                                } else {
                                    status = 'not-selected';
                                }
                                return { [row.id]: { status } }
                            });
                        break;
                    }
                    case 'multiselect': {
                        // only toggled row is changed
                        change = [{ [row.id]: { status: nextStatus } }];
                        break;
                    }
                    case 'focus': {
                        let focusedRow = getters['focusedRow'];
                        let togglingFocusedRow = focusedRow
                            ? focusedRow.id == row.id
                            : false;
                        if (focusedRow && !togglingFocusedRow) {
                            change = [
                                // defocus the focused row
                                { [focusedRow.id]: { status: 'fully-selected' } },
                                // focus the toggled row
                                { [row.id]: { status: nextStatus } },
                            ];
                        } else {
                            // only toggled row is changed
                            change = [
                                { [row.id]: { status: nextStatus } }
                            ];
                        }
                        break;
                    }
                }
                // iterate state
                dispatch('tick', { change });
            },
            selectNone({ dispatch, getters }) {
                let selected = getters['selectedRows'];
                selected.forEach(row => dispatch('toggle', row));
                dispatch('unload');
            },
            async syncToParent({ dispatch, getters, rootState }, { mutation, payload }) {
                if (getters['missingFilters']) {
                    let {
                        change: parentChange
                    } = payload;
                    let parent = mutation.split("/").slice(0, -1).join("/");
                    await rootState.api.call({
                        endpoint: endpoint('read', 'request'),
                        onSuccess: async (resp) => {
                            let load =
                                resp.map(row => ({
                                    ...row,
                                    ...getters['propagateStatusDown'](row)
                                }));
                            let change = parentChange
                                ? getters['propagateChangeDown'](parent, parentChange)
                                : null;
                            await dispatch('tick', { load, change });
                        }
                    }, getters['missingFilters']);
                }
            },
            async syncToChild({ dispatch, getters }, { mutation, payload }) {
                let { change: childChange } = payload;
                let child = mutation.split("/").slice(0, -1).join("/");
                let change = getters['propagateChangeUp'](child, childChange);
                await dispatch('tock', { change });
            },
            ...actions,
        },
        getters: {
            // data
            rowById: (state) =>
                (id) => state.rows
                    .filter(row => row.id == id)[0],
            rowsByIds: (state) =>
                (ids) => state.rows
                    .filter(row => ids.includes(row.id)),
            parentRows: (state, getters, rootState, rootGetters) =>
                (parent, rows = null) => {
                    let allParentRows = rootGetters['getPath'](parent + '/rows');
                    if (rows) {
                        let parentId = (row) => {
                            let parentIdField = path.toCamelCase(parent) + 'Id';
                            return row[parentIdField];
                        }
                        return rows.map(
                            row => allParentRows
                                .filter(parentRow => parentRow.id == parentId(row))
                        ).flat();
                    } else {
                        return allParentRows;
                    }
                },
            childRows: (state, getters, rootState, rootGetters) =>
                (child, rows = null) => {
                    let allChildRows = rootGetters['getPath'](child + '/rows');
                    if (rows) {
                        let ownIdField = path.toCamelCase(namespace) + 'Id';
                        return rows.map(
                            row => allChildRows
                                .filter(childRow => childRow[ownIdField] == row.id)
                        ).flat();
                    } else {
                        return allChildRows;
                    }
                },
            select: (state) =>
                (filters) => {
                    return filters
                        ? state.rows.filter(
                            (row) => {
                                let fullMatch = Object
                                    .entries(filters)
                                    .every(
                                        ([field, filter]) => (row[field] == filter)
                                    );
                                return fullMatch;
                            }
                        )
                        : state.rows;
                },
            list: (state, getters, rootState) =>
                // query backend without loading into the store
                (filters) => {
                    return rootState.api.call({
                        endpoint: path.toSnakeCase(namespace) + '_read_request',
                    }, filters);
                },
            // filters
            missingFilters: (state, getters) => {
                let active, filters;
                if (loadWhen == 'always') {
                    return {};
                }
                if (loadWhen == 'parent-loaded') {
                    active = () => true;
                } else if (loadWhen == 'parent-selected') {
                    active = (row) => selectedStatuses
                        .includes(row.status)
                }
                if (parents) {
                    filters = parents
                        .map(parent => {
                            let linkingIdField = path.toCamelCase(parent) + 'Id';
                            let activeParentIds = getters['parentRows'](parent)
                                .filter(active)
                                .map(row => row.id);
                            if (activeParentIds.length > 0) {
                                return { [linkingIdField]: activeParentIds }
                            }
                        })
                        .reduce((i, j) => ({ ...i, ...j }), {});
                } else {
                    filters = {}
                }
                filters = { ...filters, ...getters['paramFilters'] }
                if (Object.keys(filters).length == 0) {
                    return null;
                } else {
                    let exclude = state.rows.map(row => row.id);
                    if (exclude.length > 0) {
                        filters.exclude = exclude;
                    }
                    return filters;
                }
            },
            paramFilters: (state, getters, rootState, rootGetters) => {
                let filters = {};
                if (params) {
                    for (const [key, path] of Object.entries(params)) {
                        filters[key] = rootGetters['getPath'](path);
                    }
                }
                return filters;
            },
            // status
            status: (state) =>
                (id) => state.rows
                    .filter(row => row.id == id)[0]
                    .status,
            propagateStatusDown: (state, getters) =>
                (row) => {
                    if (!parents || singleSelect) return { status: 'not-selected' };
                    // get parent statuses
                    let parentStatuses = parents.map(
                        parent => getters['parentRows'](parent, [row])
                            .map(parentRow => parentRow.status)
                    ).flat();
                    // construct logic helpers
                    let everyParent = (...statuses) => parentStatuses
                        .every(s => statuses.includes(s));
                    let someParent = (...statuses) => parentStatuses
                        .some(s => statuses.includes(s))
                    // compute next status from parent statuses
                    if (someParent('not-selected')) {
                        return { status: 'not-selected' };
                    } else if (everyParent('fully-selected', 'in-focus')) {
                        return { status: 'fully-selected' };
                    } else {
                        console.warn('Selection in a bad state')
                    }
                },
            propagateChangeDown: (state, getters, rootState, rootGetters) =>
                (parent, parentChange) => {
                    let changedParentIds = parentChange.map(c => Object.keys(c)).flat();
                    let changedParentRows =
                        rootGetters[parent + '/rowsByIds'](changedParentIds);
                    let changedRows =
                        rootGetters[parent + '/childRows'](namespace, changedParentRows);
                    let change = changedRows.map(
                        row => ({ [row.id]: getters['propagateStatusDown'](row) })
                    );
                    return change;
                },
            propagateStatusUp: (state, getters) =>
                (row) => {
                    // get child statuses
                    let childStatuses = children.map(
                        child => getters['childRows'](child, [row])
                            .map(childRow => childRow.status)
                    ).flat()
                    // construct logic helper
                    let everyChild = (...statuses) => childStatuses
                        .every(s => statuses.includes(s));
                    // compute next status from child statuses
                    if (everyChild('fully-selected', 'in-focus')) {
                        if (row.status == 'in-focus') {
                            return { status: 'in-focus' };
                        } else {
                            return { status: 'fully-selected' };
                        }
                    } else if (everyChild('not-selected')) {
                        return { status: 'not-selected' };
                    } else {
                        return { status: 'partially-selected' };
                    }
                },
            propagateChangeUp: (state, getters, rootState, rootGetters) =>
                (child, childChange) => {
                    let changedChildIds = childChange.map(c => Object.keys(c)).flat();
                    let changedChildRows =
                        rootGetters[child + '/rowsByIds'](changedChildIds);
                    let changedRows =
                        rootGetters[child + '/parentRows'](namespace, changedChildRows);
                    let change = changedRows.map(
                        row => ({ [row.id]: getters['propagateStatusUp'](row) })
                    );
                    return change;
                },
            // selection
            selected: () =>
                (row) => selectedStatuses.includes(row.status),
            selectedRows: (state, getters) =>
                state.rows.filter(getters['selected']),
            selectedIds: (state, getters) =>
                getters['selectedRows'].map(row => row.id),
            selectedRow: (state, getters) => {
                let selectedRows = getters['selectedRows'];
                if (singleSelect) {
                    switch (selectedRows.length) {
                        case 0: return null
                        case 1: return selectedRows[0]
                        default: {
                            console.error(
                                `${namespace} is configured for singleSelect`
                                + `but multiple rows are selected; the module`
                                + `is likely in a bad state.`
                            )
                        }
                    }
                } else {
                    switch (selectedRows.length) {
                        case 0: return null
                        case 1: return selectedRows[0]
                        default: return null
                    }
                }
            },
            selectedId: (state, getters) => {
                if (singleSelect) {
                    let selectedRow = getters['selectedRow'];
                    return selectedRow ? selectedRow.id : null;
                } else {
                    console.error(
                        `${namespace} is not configured with singleSelect;`
                        + `use selectedIds or reconfigure the store module`
                    );
                }

            },
            // focus
            focused: () =>
                (row) => row.status == 'in-focus',
            focusedRow: (state, getters) => {
                let rowsFocused = state.rows.filter(getters['focused']);
                switch (rowsFocused.length) {
                    case 0: return null;
                    case 1: return rowsFocused[0];
                    default: {
                        console.warning(`More than one ${namespace} row is focused`);
                    }
                }
            },
            focusedId: (state, getters) =>
                getters['focusedRow'].id,
            // helpers
            uniqueRow: (state, getters) => {
                if (getters['focusedRow']) {
                    return getters['focusedRow'];
                } else if (getters['selectedRow']) {
                    return getters['selectedRow'];
                } else {
                    return null;
                }
            },
            ...getters,
        },
        watchers: {
            [namespace + '/$event']: namespace + '/syncToEvent',
            ...watchers,
        },
        subs: {
            ...path.zipMaps([
                {
                    from: parents,
                    sources: ['TICK'],
                    to: namespace,
                    target: 'syncToParent',
                }, {
                    from: children,
                    sources: ['TOCK'],
                    to: namespace,
                    target: 'syncToChild'
                }, {
                    from: parents,
                    sources: ['UNLOAD'],
                    to: namespace,
                    target: 'unload'
                }
            ]),
            ...subs
        },
        modules
    }
}
