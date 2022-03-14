import table from "$lib/table";
import selection from "$lib/selection";

export default {
    namespaced: true,
    state: () => ({
        // meta
        levels: ["compound", "ion", "isotope"],
        cols: [
            { field: "id", label: "ID" },
            { field: "name", label: "Name" },
            { field: "formula", label: "Formula" },
            { field: "ionMech", label: "Ion. Mech." },
            { field: "mz", label: "m/z" },
            { field: "matchScore", label: "Match score" },
            { field: "checked", label: "Checked" }
        ],
        // data
        compoundRows: [],
        ionRows: [],
        isotopeRows: [],
        // parameters
        paramMinIsoAbu: 1,
        // API
        $compoundMatchScoreRequest: {},
        $compoundMatchScoreResponse: {},
        $ionCalculationRequest: {},
        $ionCalculationResponse: {},
        // client
        ionMechs: [],
        defaultIonMechs: ["-H-", "+Br-"],
        targetsToImport: {},

    }),
    mutations: {
        addRows(state, { level, rows }) {
            let levelRows = level + 'Rows';
            let _selected = 'none';
            for (let row of rows) {
                let id = table.genId();
                state[levelRows].push({ id, _selected, ...row });
            }
        },
        removeRows(state, { level, ids }) {
            let levelRows = level + 'Rows';
            for (let id of ids) {
                let row = table.get(state[levelRows], { id });
                state[levelRows].splice(row);
            }
        },
        // ion calculation
        requestIonCalc(state) {
            state.$ionCalculationRequest = {
                requestId: table.genId(),
                minIsoAbu: state.paramMinIsoAbu,
                ionizationMechanisms: state.ionMechs,
                compounds: state.compoundRows
            };
        },
        handleIonCalcResponse(state) {
            let response = state.$ionCalculationResponse;
            if (response) {
                let _selected = 'none';
                state.ionRows = response.ions
                    .map(ion => ({ ...ion, _selected }));
                state.isotopeRows = response.isotopes
                    .map(isotope => ({ ...isotope, _selected }));
                response = null;
            }
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
    },
    actions: {
        add({ commit }, { compounds }) {
            commit('addRows', { level: 'compound', rows: compounds });
            commit('requestIonCalc');
        },
        // selection
        compoundSelectionToggle({ state, commit }, compound) {
            let nextSelection = selection.propegateDown(compound);
            // toggle compound selection
            commit('selectionSet', {
                level: 'compound',
                ids: [compound.id],
                selected: nextSelection
            });
            // toggle child ion selection
            let childIons = table.select(state.ionRows, { compoundId: compound.id });
            let nextChildSelection = nextSelection;
            commit('selectionSet', {
                level: 'ion',
                ids: childIons.map(row => row.id),
                selected: nextChildSelection,
            });
            // toggle child isotope selection
            let childIsotopes = childIons.map(ionRow => {
                return table.select(state.isotopeRows, { ionId: ionRow.id });
            }).flat();
            commit('selectionSet', {
                level: 'isotope',
                ids: childIsotopes.map(row => row.id),
                selected: nextChildSelection
            })
        },
        ionSelectionToggle({ state, commit }, ion) {
            let nextSelection = selection.propegateDown(ion);
            // toggle ion selection
            commit('selectionSet', {
                level: 'ion',
                ids: [ion.id],
                selected: nextSelection,
            });
            // toggle child isotope selection
            let childIsotopes = table.select(state.isotopeRows, { ionId: ion.id });
            let nextChildSelection = nextSelection;
            commit('selectionSet', {
                level: 'isotope',
                ids: childIsotopes.map(row => row.id),
                selected: nextChildSelection,
            });
            // toggle parent compound selection
            let syblingIonRows = table.select(state.ionRows,
                { compoundId: ion.compoundId }
            );
            let nextParentSelection = selection.propegateUp(syblingIonRows);
            commit('selectionSet', {
                level: 'compound',
                ids: [ion.compoundId],
                selected: nextParentSelection,
            })
        },
        isotopeSelectionToggle({ state, commit }, isotope) {
            let nextSelection = selection.propegateDown(isotope);
            // toggle isotope selection
            commit('selectionSet', {
                level: 'isotope',
                ids: [isotope.id],
                selected: nextSelection
            })
            // toggle parent ion selection
            let syblingIsotopeRows = table.select(state.isotopeRows,
                { ionId: isotope.ionId }
            );
            let nextParentIonSelection = selection.propegateUp(syblingIsotopeRows);
            commit('selectionSet', {
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
            commit('selectionSet', {
                level: 'compound',
                ids: [ionRow.compoundId],
                selected: nextParentCompoundSelection
            })
        },
    },
    getters: {
        // selected
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
        // stats
        stats: (state, getters) =>
            ({ level = 'compound', selected = true }) => {
                return getters[level + 'Stats']({ selected });
            },
        compoundStats: (state, getters, rootState, rootGetters) =>
            ({ selected = true }) => {
                let matchesExist = rootState.match.compoundRows.length > 0;
                if (matchesExist) {
                    let matches = rootGetters['match/ratings']({
                        level: 'compound', selected
                    });
                    let targets = selected ? getters['compoundsSelected'] : state.compoundRows;
                    let total = table.query(
                        `
                            select
                                m.targetCompoundId as id
                                ,max(m.matchScore) as matchScore
                                ,max(m.samplePeakHeight) as peakHeight
                                ,count(distinct m.sampleItemId) as matchCompoundTotalCount
                            from matches m
                            group by m.targetCompoundId
                        `,
                        { matches }
                    );
                    let probable = table.query(
                        `
                            select
                                m.targetCompoundId as id
                                ,count(distinct m.sampleItemId) as matchCompoundProbableCount
                            from matches m
                            where rating = 'probable'
                            group by m.targetCompoundId
                        `,
                        { matches }
                    );
                    let possible = table.query(
                        `
                            select
                                m.targetCompoundId as id
                                ,count(distinct m.sampleItemId) as matchCompoundPossibleCount
                            from matches m
                            where rating = 'possible'
                            group by m.targetCompoundId
                        `,
                        { matches }
                    );
                    let result = table.query(
                        `
                        select
                            tar.*    
                            ,coalesce(tot.matchScore, 0) as matchScore
                            ,coalesce(tot.peakHeight, 0) as peakHeight
                            ,coalesce(tot.matchCompoundTotalCount, 0) as matchCompoundTotalCount
                            ,coalesce(prob.matchCompoundProbableCount, 0) as matchCompoundProbableCount
                            ,coalesce(poss.matchCompoundPossibleCount,0) as matchCompoundPossibleCount
                        from targets tar
                        left join total tot
                            on tar.id = tot.id
                        left join probable prob
                            on tar.id = prob.id
                        left join possible poss
                            on tar.id = poss.id
                    `, { targets, total, probable, possible }
                    );
                    if (rootState.dev.logGetters) console.table(result);
                    return result;
                } else {
                    return state.compoundRows;
                }
            },
        ionStats: (state, getters, rootState, rootGetters) =>
            ({ selected = true }) => {
                let matchesExist = rootState.match.ionRows.length > 0;
                if (matchesExist) {
                    let matches = rootGetters['match/ratings']({
                        level: 'ion', selected
                    });
                    let targets = selected ? getters['ionsSelected'] : state.ionRows;
                    let total = table.query(
                        `
                            select
                                m.targetIonId as id
                                ,max(m.matchScore) as matchScore
                                ,max(m.samplePeakHeight) as peakHeight
                                ,count(distinct m.sampleItemId) as matchIonTotalCount
                            from matches m
                            group by m.targetIonId
                        `,
                        { matches }
                    );
                    let probable = table.query(
                        `
                            select
                                m.targetIonId as id
                                ,count(distinct m.sampleItemId) as matchIonProbableCount

                            from matches m
                            where rating = 'probable'
                            group by m.targetIonId
                        `,
                        { matches }
                    );
                    let possible = table.query(
                        `
                            select
                                m.targetIonId as id
                                ,count(distinct m.sampleItemId) as matchIonPossibleCount
                            from matches m
                            where rating = 'possible'
                            group by m.targetIonId
                        `,
                        { matches }
                    );
                    let result = table.query(
                        `
                        select
                            tar.*    
                            ,coalesce(tot.matchScore, 0) as matchScore
                            ,coalesce(tot.peakHeight, 0) as peakHeight
                            ,coalesce(tot.matchIonTotalCount, 0) as matchIonTotalCount
                            ,coalesce(prob.matchIonProbableCount, 0) as matchIonProbableCount
                            ,coalesce(poss.matchIonPossibleCount,0) as matchIonPossibleCount
                        from targets tar
                        left join total tot
                            on tar.id = tot.id
                        left join probable prob
                            on tar.id = prob.id
                        left join possible poss
                            on tar.id = poss.id
                    `, { targets, total, probable, possible }
                    );
                    if (rootState.dev.logGetters) console.table(result);
                    return result;
                } else {
                    return state.ionRows;
                }
            },
        isotopeStats: (state, getters, rootState, rootGetters) =>
            ({ selected = true }) => {
                let matchesExist = rootState.match.isotopeRows.length > 0;
                if (matchesExist) {
                    let matches = rootGetters['match/ratings']({
                        level: 'isotope', selected
                    });
                    let targets = selected ? getters['isotopesSelected'] : state.isotopeRows;
                    let total = table.query(
                        `
                            select
                                m.targetIsotopeId as id
                                ,max(m.matchScore) as matchScore
                                ,max(m.samplePeakHeight) as peakHeight
                                ,count(distinct m.sampleItemId) as matchIsotopeTotalCount
                            from matches m
                            group by m.targetIsotopeId
                        `,
                        { matches }
                    );
                    let probable = table.query(
                        `
                            select
                                m.targetIsotopeId as id
                                ,count(distinct m.sampleItemId) as matchIsotopeProbableCount
                            from matches m
                            where rating = 'probable'
                            group by m.targetIsotopeId
                        `,
                        { matches }
                    );
                    let possible = table.query(
                        `
                            select
                                m.targetIsotopeId as id
                                ,count(distinct m.sampleItemId) as matchIsotopePossibleCount
                            from matches m
                            where rating = 'possible'
                            group by m.targetIsotopeId
                        `,
                        { matches }
                    );
                    let result = table.query(
                        `
                        select
                            tar.*    
                            ,coalesce(tot.matchScore, 0) as matchScore
                            ,coalesce(tot.peakHeight, 0) as peakHeight
                            ,coalesce(tot.matchIsotopeTotalCount, 0) as matchIsotopeTotalCount
                            ,coalesce(prob.matchIsotopeProbableCount, 0) as matchIsotopeProbableCount
                            ,coalesce(poss.matchIsotopePossibleCount,0) as matchIsotopePossibleCount
                        from targets tar
                        left join total tot
                            on tar.id = tot.id
                        left join probable prob
                            on tar.id = prob.id
                        left join possible poss
                            on tar.id = poss.id
                    `, { targets, total, probable, possible }
                    );
                    if (rootState.dev.logGetters) console.table(result);
                    return result;
                } else {
                    return state.isotopeRows;
                }
            },
    }
}