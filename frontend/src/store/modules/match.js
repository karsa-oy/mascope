import table from '$lib/table';
import { handleCalls } from '$lib/api';

export default {
    namespaced: true,
    state: {
        compoundRows: [],
        ionRows: [],
        isotopeRows: [],
        // match params
        paramProbableMatchThreshold: 0.9,
        paramPossibleMatchThreshold: 0.5,
        paramMzTolerance: 100, // ppm
        paramIsoRatioTolerance: 10, // %
        // peak params
        paramPeakMinIntensity: 1,
        paramPeakMinSeparation: 3,
        paramMzRange: null,
        paramTRange: null,
        // API
        $request: {},
    },
    mutations: {
        add(state, { matches }) {
            state.compoundRows.push(...matches.compound);
            state.ionRows.push(...matches.ion);
            state.isotopeRows.push(...matches.isotope);
        },
        remove(state, { level, sampleItemIds }) {
            let levelRows = level + 'Rows';
            state[levelRows] = state[levelRows].filter(
                (row) => !sampleItemIds.includes(row.sampleItemId)
            );
        }
    },
    actions: {
        // add
        async request({ state, dispatch, rootState }, batch) {
            // prepare sample items
            let sampleItems = table
                .select(rootState.sample.itemRows, { batchId: batch.id });
            // prepare targets
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
            // prepare parameters
            let params = {
                // match params
                mzTolerance: state.paramMzTolerance,
                isoAbuTolerance: state.paramIsoRatioTolerance,
                // peak params
                mzRange: state.paramMzRange,
                tRange: state.paramTRange,
                minPeakIntensity: state.paramPeakMinIntensity,
                minPeakSeparation: state.paramPeakMinSeparation,
            }
            // request matches
            handleCalls({
                api: rootState.api,
                name: 'match_request',
                values: sampleItems.map((sampleItem) => {
                    return {
                        requestId: table.genId(),
                        sampleItem,
                        targetIsotopes,
                        ...params
                    }
                }),
                handler: async (response) => {
                    await dispatch('match/handleResponse', response, { root: true });
                }
            });
        },
        // remove
        async handleResponse({ commit }, response) {
            if (response) {
                await commit('add', { matches: response });
            }
        },
        async clear({ commit, rootState }, batch) {
            let sampleItemIds = table
                .select(rootState.sample.itemRows, { batchId: batch.id })
                .map(item => item.id);
            commit('remove', { level: 'compound', sampleItemIds });
            commit('remove', { level: 'ion', sampleItemIds });
            commit('remove', { level: 'isotope', sampleItemIds });
        },
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