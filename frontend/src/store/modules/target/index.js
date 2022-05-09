import focus from "./focus";
import stat from "./stat";
import param from "./param";

import table from "$lib/table";
import selection from "$lib/selection";

// TODO - seperate selection logic into a submodule
export default {
    namespaced: true,
    state: {
        compoundRows: [],
        ionRows: [],
        isotopeRows: [],
        // client
        ionMechs: [],
        defaultIonMechs: ["-H-", "+Br-"],
        targetsToImport: {},
    },
    mutations: {
        ADD(state, { level, rows }) {
            let levelRows = level + 'Rows';
            let _selected = 'none';
            for (let row of rows) {
                let id = table.genId();
                state[levelRows].push({ id, _selected, ...row });
            }
        },
        REMOVE(state, { level, ids }) {
            let levelRows = level + 'Rows';
            for (let id of ids) {
                let row = table.get(state[levelRows], { id });
                state[levelRows].splice(row);
            }
        },
        // ion calculation
        LOAD_IONS_AND_ISOTOPES(state, response) {
            let _selected = 'none';
            state.ionRows = response.ions
                .map(ion => ({ ...ion, _selected }));
            state.isotopeRows = response.isotopes
                .map(isotope => ({ ...isotope, _selected }));
        },
        // selection
        SET_SELECTION(state, { level, ids, selected }) {
            let levelRows = level + 'Rows';
            for (let id of ids) {
                table.update(state[levelRows],
                    { id, _selected: selected },
                    { partial: true }
                );
            }
        },
    },
    actions: {
        async add({ commit, state, rootState }, { compounds }) {
            await commit('ADD', { level: 'compound', rows: compounds });
            await rootState.api.call({
                endpoint: 'target_ion_calculation_request',
                onSuccess: (response) => commit('LOAD_IONS_AND_ISOTOPES', response)
            }, {
                requestId: table.genId(),
                minIsoAbu: rootState.target.param.minIsoAbu,
                ionizationMechanisms: state.ionMechs,
                compounds: state.compoundRows
            })
        },
        // selection
        compoundSelectionToggle({ state, commit }, compound) {
            let nextSelection = selection.propegateDown(compound);
            // toggle compound selection
            commit('SET_SELECTION', {
                level: 'compound',
                ids: [compound.id],
                selected: nextSelection
            });
            // toggle child ion selection
            let childIons = table.select(state.ionRows, { compoundId: compound.id });
            let nextChildSelection = nextSelection;
            commit('SET_SELECTION', {
                level: 'ion',
                ids: childIons.map(row => row.id),
                selected: nextChildSelection,
            });
            // toggle child isotope selection
            let childIsotopes = childIons.map(ionRow => {
                return table.select(state.isotopeRows, { ionId: ionRow.id });
            }).flat();
            commit('SET_SELECTION', {
                level: 'isotope',
                ids: childIsotopes.map(row => row.id),
                selected: nextChildSelection
            })
        },
        ionSelectionToggle({ state, commit }, ion) {
            let nextSelection = selection.propegateDown(ion);
            // toggle ion selection
            commit('SET_SELECTION', {
                level: 'ion',
                ids: [ion.id],
                selected: nextSelection,
            });
            // toggle child isotope selection
            let childIsotopes = table.select(state.isotopeRows, { ionId: ion.id });
            let nextChildSelection = nextSelection;
            commit('SET_SELECTION', {
                level: 'isotope',
                ids: childIsotopes.map(row => row.id),
                selected: nextChildSelection,
            });
            // toggle parent compound selection
            let syblingIonRows = table.select(state.ionRows,
                { compoundId: ion.compoundId }
            );
            let nextParentSelection = selection.propegateUp(syblingIonRows);
            commit('SET_SELECTION', {
                level: 'compound',
                ids: [ion.compoundId],
                selected: nextParentSelection,
            })
        },
        isotopeSelectionToggle({ state, commit }, isotope) {
            let nextSelection = selection.propegateDown(isotope);
            // toggle isotope selection
            commit('SET_SELECTION', {
                level: 'isotope',
                ids: [isotope.id],
                selected: nextSelection
            })
            // toggle parent ion selection
            let syblingIsotopeRows = table.select(state.isotopeRows,
                { ionId: isotope.ionId }
            );
            let nextParentIonSelection = selection.propegateUp(syblingIsotopeRows);
            commit('SET_SELECTION', {
                level: 'ion',
                ids: [isotope.ionId],
                selected: nextParentIonSelection,
            });
            // toggle parent compound selection
            let ionRow = table.get(state.ionRows,
                { id: isotope.ionId }
            );
            let syblingIonRows = table.select(state.ionRows,
                { compoundId: ionRow.compoundId }
            );
            let nextParentCompoundSelection = selection.propegateUp(syblingIonRows);
            commit('SET_SELECTION', {
                level: 'compound',
                ids: [ionRow.compoundId],
                selected: nextParentCompoundSelection
            })
        },
    },
    getters: {
        // selection
        selected: (state, getters) =>
            ({ level }) => {
                return getters[level + 'Selected'];
            },
        compoundsSelected: function (state) {
            let selected = (row) => ['all', 'some'].includes(row._selected)
            let compoundsSelected = state.compoundRows.filter(selected);
            return compoundsSelected.length > 0 ? compoundsSelected : state.compoundRows;
        },
        ionsSelected: function (state) {
            let selected = (row) => ['all', 'some'].includes(row._selected)
            let ionsSelected = state.ionRows.filter(selected);
            return ionsSelected.length > 0 ? ionsSelected : state.ionRows;
        },
        isotopesSelected: function (state) {
            let selected = (row) => ['all', 'some'].includes(row._selected)
            let isotopesSelected = state.isotopeRows.filter(selected);
            return isotopesSelected.length > 0 ? isotopesSelected : state.isotopeRows;
        },
        status: (state, getters, rootState) =>
            (row) => {
                let selected = row._selected;
                let focusRow = rootState
                    .target.focus.row
                let focused = focusRow
                    ? focusRow.id == row.id
                    : false;
                if (!focused) {
                    switch (selected) {
                        case 'none': return 'not-selected';
                        case 'some': return 'partially-selected';
                        case 'all': return 'fully-selected';
                        default: {
                            console.warn(`Target selection in a bad state;`, {
                                selected,
                                focused
                            });
                            return;
                        }
                    }
                } else if (focused) {
                    if (selected == 'all' || selected == 'some') {
                        return 'focused';
                    } else {
                        console.warn(`Target selection in a bad state;`, {
                            selected,
                            focused
                        });
                        return;
                    }
                } else {
                    console.warn(`Target selection in a bad state;`, {
                        selected,
                        focused
                    });
                    return;
                }
            }
    },
    modules: {
        focus,
        stat,
        param,
    }
}