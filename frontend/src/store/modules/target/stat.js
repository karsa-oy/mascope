import table from "$lib/table";

export default {
    namespaced: true,
    getters: {
        // stats
        rows: (state, getters) =>
            ({ level = 'compound', selected = true, itemFocused = false }) => {
                return getters[level + 's']({ selected, itemFocused });
            },
        compounds: (state, getters, rootState, rootGetters) =>
            ({ selected = true, itemFocused = false }) => {
                let matchesExist = rootState.match.compoundRows.length > 0;
                if (matchesExist) {
                    let matches = rootGetters['match/rating/rows']({
                        level: 'compound', selected
                    });
                    if (itemFocused) {
                        if (!rootState.sample.item.focus.row) return rootState.target.compoundRows; 
                        matches = matches.filter(
                            (m) => m.sampleItemId === rootState.sample.item.focus.row.id
                            );
                    }
                    let compounds = selected ? rootGetters['target/compoundsSelected'] : rootState.target.compoundRows;
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
                    return rootState.target.compoundRows;
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
                        if (!rootState.sample.item.focus.row) return rootState.target.ionRows; 
                        matches = matches.filter(
                            (m) => m.sampleItemId === rootState.sample.item.focus.row.id
                            );
                    }
                    let ions = selected ? rootGetters['target/ionsSelected'] : rootState.target.ionRows;
                    let compounds = selected ? rootGetters['target/compoundsSelected'] : rootState.target.compoundRows;
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
                    return rootState.target.ionRows;
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
                        if (!rootState.sample.item.focus.row) return rootState.target.isotopeRows; 
                        matches = matches.filter(
                            (m) => m.sampleItemId === rootState.sample.item.focus.row.id
                            );
                    }
                    let isotopes = selected ? rootGetters['target/isotopesSelected'] : rootState.target.isotopeRows;
                    let ions = selected ? rootGetters['target/ionsSelected'] : rootState.target.ionRows;
                    let compounds = selected ? rootGetters['target/compoundsSelected'] : rootState.target.compoundRows;
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
                    return rootState.target.isotopeRows;
                }
            },
    }
}