import table from "$lib/table";

export default {
    namespaced: true,
    getters: {
        // stats
        rows: (state, getters) =>
            ({ level = 'compound', selected = true, itemFocused = false }) => {
                return getters[level + 's']({ selected, itemFocused });
            },
        collections: (state, getters, rootState, rootGetters) =>
            ({ selected = true, itemFocused = false }) => {
                let matchesExist = rootState.match.collectionRows.length > 0;
                if (matchesExist) {
                    let matches = rootGetters['match/rating/rows']({
                        level: 'collection', selected
                    });
                    if (itemFocused) {
                        if (!rootState.sample.item.focusedRow) return rootState.target.collection.rows;
                        matches = matches.filter(
                            (m) => m.sampleItemId === rootState.sample.item.focusedRow.id
                        );
                    }
                    let collections = selected ? rootGetters['target/collection/selectedRows'] : rootState.target.collection.rows;
                    let total = table.query(
                        `
                            select
                                m.targetCollectionId as id
                                ,max(m.matchScore) as matchScore
                                ,max(m.samplePeakHeight) as peakHeight
                                ,count(distinct m.sampleItemId) as matchCollectionTotalCount
                            from matches m
                            group by m.targetCollectionId
                        `,
                        { matches }
                    );
                    let probable = table.query(
                        `
                            select
                                m.targetCollectionId as id
                                ,count(distinct m.sampleItemId) as matchCollectionProbableCount
                            from matches m
                            where rating = 'probable'
                            group by m.targetCollectionId
                        `,
                        { matches }
                    );
                    let possible = table.query(
                        `
                            select
                                m.targetCollectionId as id
                                ,count(distinct m.sampleItemId) as matchCollectionPossibleCount
                            from matches m
                            where rating = 'possible'
                            group by m.targetCollectionId
                        `,
                        { matches }
                    );
                    let result = table.query(
                        `
                        select
                            com.*    
                            ,coalesce(tot.matchScore, 0) as matchScore
                            ,coalesce(tot.peakHeight, 0) as peakHeight
                            ,coalesce(tot.matchCollectionTotalCount, 0) as matchCollectionTotalCount
                            ,coalesce(prob.matchCollectionProbableCount, 0) as matchCollectionProbableCount
                            ,coalesce(poss.matchCollectionPossibleCount,0) as matchCollectionPossibleCount
                        from collections com
                        left join total tot
                            on com.id = tot.id
                        left join probable prob
                            on com.id = prob.id
                        left join possible poss
                            on com.id = poss.id
                    `, { collections, total, probable, possible }
                    );
                    if (rootState.dev.logGetters) console.table(result);
                    return result;
                } else {
                    return rootState.target.collection.rows;
                }
            },
        compounds: (state, getters, rootState, rootGetters) =>
            ({ selected = true, itemFocused = false }) => {
                let matchesExist = rootState.match.compoundRows.length > 0;
                if (matchesExist) {
                    let matches = rootGetters['match/rating/rows']({
                        level: 'compound', selected
                    });
                    if (itemFocused) {
                        let focusedSample = rootGetters['sample/item/focusedRow'];
                        if (!focusedSample) return rootGetters['target/compound/rows'];
                        matches = matches.filter(
                            (m) => m.sampleItemId === focusedSample.id
                        );
                    }
                    let compounds = selected ? rootGetters['target/compound/selectedRows'] : rootState.target.compound.rows;
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
                            com.*    
                            ,coalesce(tot.matchScore, 0) as matchScore
                            ,coalesce(tot.peakHeight, 0) as peakHeight
                            ,coalesce(tot.matchCompoundTotalCount, 0) as matchCompoundTotalCount
                            ,coalesce(prob.matchCompoundProbableCount, 0) as matchCompoundProbableCount
                            ,coalesce(poss.matchCompoundPossibleCount,0) as matchCompoundPossibleCount
                        from compounds com
                        left join total tot
                            on com.id = tot.id
                        left join probable prob
                            on com.id = prob.id
                        left join possible poss
                            on com.id = poss.id
                    `, { compounds, total, probable, possible }
                    );
                    if (rootState.dev.logGetters) console.table(result);
                    return result;
                } else {
                    return rootState.target.compound.rows;
                }
            },
        ions: (state, getters, rootState, rootGetters) =>
            ({ selected = true, itemFocused = false }) => {
                let matchesExist = rootState.match.ionRows.length > 0;
                if (matchesExist) {
                    let matches = rootGetters['match/rating/rows']({
                        level: 'ion', selected
                    });
                    if (itemFocused) {
                        let focusedSample = rootGetters['sample/item/focusedRow'];
                        if (!focusedSample) return rootGetters['target/ion/rows'];
                        matches = matches.filter(
                            (m) => m.sampleItemId === focusedSample.id
                        );
                    }
                    let ions = selected ? rootGetters['target/ion/selectedRows'] : rootState.target.ion.rows;
                    let compounds = selected ? rootGetters['target/compound/selectedRows'] : rootState.target.compound.rows;
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
                            ion.*    
                            ,com.formula as compoundFormula
                            ,com.name as compoundName
                            ,coalesce(tot.matchScore, 0) as matchScore
                            ,coalesce(tot.peakHeight, 0) as peakHeight
                            ,coalesce(tot.matchIonTotalCount, 0) as matchIonTotalCount
                            ,coalesce(prob.matchIonProbableCount, 0) as matchIonProbableCount
                            ,coalesce(poss.matchIonPossibleCount,0) as matchIonPossibleCount
                        from ions ion
                        left join compounds com
                            on ion.compoundId = com.id
                        left join total tot
                            on ion.id = tot.id
                        left join probable prob
                            on ion.id = prob.id
                        left join possible poss
                            on ion.id = poss.id
                    `, { ions, compounds, total, probable, possible }
                    );
                    if (rootState.dev.logGetters) console.table(result);
                    return result;
                } else {
                    return rootState.target.ion.rows;
                }
            },
        isotopes: (state, getters, rootState, rootGetters) =>
            ({ selected = true, itemFocused = false }) => {
                let matchesExist = rootState.match.isotopeRows.length > 0;
                if (matchesExist) {
                    let matches = rootGetters['match/rating/rows']({
                        level: 'isotope', selected
                    });
                    if (itemFocused) {
                        let focusedSample = rootGetters['sample/item/focusedRow'];
                        if (!focusedSample) return rootGetters['target/isotope/rows'];
                        matches = matches.filter(
                            (m) => m.sampleItemId === focusedSample.id
                        );
                    }
                    let isotopes = selected ? rootGetters['target/isotope/selectedRows'] : rootState.target.isotope.rows;
                    let ions = selected ? rootGetters['target/ion/selectedRows'] : rootState.target.ion.rows;
                    let compounds = selected ? rootGetters['target/compound/selectedRows'] : rootState.target.compound.rows;
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
                            iso.*
                            ,ion.formula as ionFormula
                            ,ion.ionMech as ionMech
                            ,com.formula as compoundFormula
                            ,com.name as compoundName
                            ,coalesce(tot.matchScore, 0) as matchScore
                            ,coalesce(tot.peakHeight, 0) as peakHeight
                            ,coalesce(tot.matchIsotopeTotalCount, 0) as matchIsotopeTotalCount
                            ,coalesce(prob.matchIsotopeProbableCount, 0) as matchIsotopeProbableCount
                            ,coalesce(poss.matchIsotopePossibleCount,0) as matchIsotopePossibleCount
                        from isotopes iso
                        left join ions ion
                            on iso.ionId = ion.id
                        left join compounds com
                            on ion.compoundId = com.id
                        left join total tot
                            on iso.id = tot.id
                        left join probable prob
                            on iso.id = prob.id
                        left join possible poss
                            on iso.id = poss.id
                    `, { isotopes, ions, compounds, total, probable, possible }
                    );
                    if (rootState.dev.logGetters) console.table(result);
                    return result;
                } else {
                    return rootState.target.isotope.rows;
                }
            },
    }
}