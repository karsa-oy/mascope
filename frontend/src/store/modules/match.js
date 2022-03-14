import table from '$lib/table';

export default {
    namespaced: true,
    state: {
        compoundRows: [],
        ionRows: [],
        isotopeRows: [],
        // Parameters
        paramProbableMatchThreshold: 0.9,
        paramPossibleMatchThreshold: 0.5,
        paramMzTolerance: 100, // ppm
        paramIsoRatioTolerance: 10, // %
        // API
        $request: {},
        $update: null

    },
    mutations: {
        makeRequest(state, { sampleItem, targetIsotopes }) {
            let requestId = table.genId();
            state.$request = {
                requestId,
                sampleItem,
                targetIsotopes,
                mzTolerance: state.paramMzTolerance,
                isoAbuTolerance: state.paramIsoRatioTolerance,
            };
        },
        handleUpdate(state) {
            let matchStats = state.$update.matchStats
            state.compoundRows.push(...matchStats.compound);
            state.ionRows.push(...matchStats.ion);
            state.isotopeRows.push(...matchStats.isotope);
        },
        remove(state, { level, filters }) {
            let levelRows = level + 'Rows';
            state[levelRows] = table.remove(state[levelRows], filters);
        }
    },
    actions: {
        request({ commit, rootState }, { sampleItem }) {
            let getCompoundId = (ionId) => ({
                compoundId: table.get(rootState.target.ionRows, {
                    id: ionId
                }).compoundId
            })
            let targetIsotopes = rootState.target.isotopeRows
                .map((row) => ({
                    ...row,
                    ...getCompoundId(row.ionId)
                }));
            commit('makeRequest', {
                sampleItem,
                targetIsotopes
            })
        },
        handleUpdate({ commit }) {
            commit('handleUpdate');
        },
        async removeBySampleItem({ commit }, sampleItem) {
            let filters = { sampleItemId: sampleItem.id };
            commit('remove', { level: 'compound', filters });
            commit('remove', { level: 'ion', filters });
            commit('remove', { level: 'isotope', filters });
        }
    },
    getters: {
        exists: function (state) {
            let totalMatches = state.compoundRows.length
                + state.ionRows.length
                + state.isotopeRows.length
            return totalMatches > 0;
        },
        ratings: (state, getters, rootState) =>
            ({ level = 'compound', selected = true }) => {
                let ratings = table.query(
                    `
                    select
                        m.*
                        ,(case
                            when matchScore >= ${state.paramProbableMatchThreshold}
                                then 'probable'
                            when matchScore < ${state.paramProbableMatchThreshold}
                                and matchScore >= ${state.paramPossibleMatchThreshold}
                                then 'possible'
                            when matchScore < ${state.paramPossibleMatchThreshold}
                                then 'improbable'
                            else 'unknown'
                        end) as rating
                    from matches m
                    ` ,
                    { matches: getters['joins']({ level, selected }) }
                );
                let compounds = rootState.target.compoundRows;
                let ions = rootState.target.ionRows;
                switch (level) {
                    case 'compound':
                        return ratings;
                    case 'ion':
                        return table.query(`
                            select
                                rat.*
                                ,com.name as targetCompoundName
                                ,com.formula as targetCompoundFormula
                            from ratings rat
                            left join compounds com
                                on rat.targetCompoundId = com.id
                        
                        `, { ratings, compounds });
                    case 'isotope':
                        return table.query(`
                            select
                                rat.*
                                ,com.name as targetCompoundName
                                ,com.formula as targetCompoundFormula
                                ,ion.formula as targetIonFormula
                                ,ion.ionMech as targetIonMech
                            from ratings rat
                            left join compounds com
                                on rat.targetCompoundId = com.id
                            left join ions ion
                                on rat.targetIonId = ion.id
                        
                        `, { ratings, compounds, ions });
                }
            },
        stats: (state, getters) =>
            ({ level = 'compound', selected = true }) => {
                return table.query(
                    `
                    select
                        m.rating
                        ,count(*) as matchCount
                        ,count(distinct m.sampleItemId) as sampleItemCount
                        ,count(distinct m.target${level}Id) as target${level}Count
                    from matches m
                    group by m.rating
                    order by m.rating
                    `,
                    { matches: getters['ratings']({ level, selected }) }
                );
            },
        // helper getters for internal use
        // join match data with sample items and targets
        joins: (state, getters) =>
            ({ level = 'compound', selected = true }) => {
                return getters[level + 'Joins']({ selected });
            },
        compoundJoins: (state, getters, rootState, rootGetters) =>
            ({ selected = true }) => {
                // only selected samples are stored in the match module
                let sampleItems = rootState.sample.itemRows;
                // compound level join
                let targetCompoundsSelected = selected ?
                    rootGetters['target/compoundsSelected']
                    : rootState.target.compoundRows;
                return table.query(
                    `
                    select 
                        m.*
                        ,t.name as targetName
                        ,t.formula as targetFormula
                        ,t._selected as targetSelected
                        ,s.filename as sampleFilename
                        ,s.method as sampleMethod
                        ,s.properties as sampleProperties
                    from matches m
                    inner join targets t
                        on t.id = m.targetCompoundId
                    left join samples s
                        on s.id = m.sampleItemId
                    `,
                    {
                        matches: state.compoundRows,
                        targets: targetCompoundsSelected,
                        samples: sampleItems
                    }
                );
            },
        ionJoins: (state, getters, rootState, rootGetters) =>
            ({ selected = true }) => {
                // only selected samples are stored in the match module
                let sampleItems = rootState.sample.itemRows;
                // ion level join
                let targetIonsSelected = selected ?
                    rootGetters['target/ionsSelected']
                    : rootState.target.ionRows;
                return table.query(
                    `
                    select 
                        m.*
                        ,t.compoundId as targetCompoundId
                        ,t.ionMech as targetIonMech
                        ,t.formula as targetFormula
                        ,t._selected as targetSelected
                        ,s.filename as sampleFilename
                        ,s.method as sampleMethod
                        ,s.properties as sampleProperties
                    from matches m
                    inner join targets t
                        on t.id = m.targetIonId
                    left join samples s
                        on s.id = m.sampleItemId
                    `,
                    {
                        matches: state.ionRows,
                        targets: targetIonsSelected,
                        samples: sampleItems
                    }
                );
            },
        isotopeJoins: (state, getters, rootState, rootGetters) =>
            ({ selected = true }) => {
                // only selected samples are stored in the match module
                let sampleItems = rootState.sample.itemRows;
                // isotope level join
                let targetIsotopesSelected = selected ?
                    rootGetters['target/isotopesSelected']
                    : rootState.target.isotopeRows;
                return table.query(
                    `
                    select 
                        m.*
                        ,t.ionId as targetIonId
                        ,t.relAbu as targetRelAbu
                        ,t.mz as targetMz
                        ,t._selected as targetSelected
                        ,s.filename as sampleFilename
                        ,s.method as sampleMethod
                        ,s.properties as sampleProperties
                    from matches m
                    inner join targets t
                        on t.id = m.targetIsotopeId
                    left join samples s
                        on s.id = m.sampleItemId
                    `,
                    {
                        matches: state.isotopeRows,
                        targets: targetIsotopesSelected,
                        samples: sampleItems
                    }
                );
            },
    }
}