import table from "./table";

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
    namespace,
    state,
    mutations,
    actions,
    getters,
    watchers,
    modules }) {
    return {
        namespaced: true,
        state: {
            rows: [],
            ...state
        },
        mutations: {
            LOAD(state, { rows }) {
                state.rows = table
                    .remove(state.rows, {
                        id: rows.map(row => row.id)
                    });
                state.rows
                    .push(...rows);
            },
            UNLOAD(state, { filters }) {
                state.rows = table
                    .remove(state.rows, filters);
            },
            ...mutations,
        },
        actions: {
            async create({ commit, rootState }, rows) {
                await rootState.api.call({
                    endpoint: namespace + '_create_request',
                    onSuccess: (resp) => commit('LOAD', { rows: resp }),
                }, rows);
            },
            async read({ commit, rootState }, filters) {
                await rootState.api.call({
                    endpoint: namespace + '_read_request',
                    onSuccess: (resp) => commit('LOAD', { rows: resp })
                }, filters);
            },
            async update({ commit, rootState }, rows) {
                await rootState.api.call({
                    endpoint: namespace + '_update_request',
                    onSuccess: () => commit('LOAD', { rows })
                }, rows);
            },
            async delete({ commit, rootState }, ids) {
                await rootState.api.call({
                    endpoint: namespace + '_delete_request',
                    onSuccess: () => commit('UNLOAD', { filters: { id: ids } })
                }, ids);
            },
            async clear({ commit }, filters) {
                await commit('UNLOAD', { filters });
            },
            ...actions
        },
        getters,
        watchers,
        modules
    }
}