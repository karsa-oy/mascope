import table from '$lib/table';

export default {
    namespaced: true,
    getters: {
        // join match data with sample items and targets
        rows: (state, getters) =>
            ({ level = 'compound', selected = true }) => {
                return getters[level + 's']({ selected });
            },
        compounds: (state, getters, rootState, rootGetters) =>
            ({ selected = true }) => {
                let sampleItems = rootState.sample.item.selection.rows;
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
                        matches: rootState.match.compoundRows,
                        targets: targetCompoundsSelected,
                        samples: sampleItems
                    }
                );
            },
        ions: (state, getters, rootState, rootGetters) =>
            ({ selected = true }) => {
                let sampleItems = rootState.sample.item.selection.rows;
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
                        matches: rootState.match.ionRows,
                        targets: targetIonsSelected,
                        samples: sampleItems
                    }
                );
            },
        isotopes: (state, getters, rootState, rootGetters) =>
            ({ selected = true }) => {
                let sampleItems = rootState.sample.item.selection.rows;
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
                        matches: rootState.match.isotopeRows,
                        targets: targetIsotopesSelected,
                        samples: sampleItems
                    }
                );
            },
    }
}