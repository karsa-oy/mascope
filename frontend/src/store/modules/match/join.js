import table from '$lib/table';

export default {
    namespaced: true,
    getters: {
        // join match data with sample items and targets
        rows: (state, getters) =>
            ({ level = 'compound', selected = true }) => {
                return getters[level + 's']({ selected });
            },
        collections: (state, getters, rootState, rootGetters) =>
            ({ selected = true }) => {
                let sampleItems = rootGetters['sample/item/selectedRows'];
                let targetCollectionsSelected = selected ?
                    rootGetters['target/collection/selectedRows']
                    : rootState.target.collection.rows;
                return table.query(
                    `
                    select 
                        m.*
                        ,t.name as targetName
                        ,s.filename as sampleFilename
                        ,s.method as sampleMethod
                        ,s.properties as sampleProperties
                    from matches m
                    inner join targets t
                        on t.id = m.targetCollectionId
                    left join samples s
                        on s.id = m.sampleItemId
                    `,
                    {
                        matches: rootState.match.collectionRows,
                        targets: targetCollectionsSelected,
                        samples: sampleItems
                    }
                );
            },
        compounds: (state, getters, rootState, rootGetters) =>
            ({ selected = true }) => {
                let sampleItems = rootGetters['sample/item/selectedRows'];
                let targetCompoundsSelected = selected ?
                    rootGetters['target/compound/selectedRows']
                    : rootState.target.compound.rows;
                return table.query(
                    `
                    select 
                        m.*
                        ,t.name as targetName
                        ,t.formula as targetFormula
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
                let sampleItems = rootGetters['sample/item/selectedRows'];
                let targetIonsSelected = selected ?
                    rootGetters['target/ion/selectedRows']
                    : rootState.target.ion.rows;
                return table.query(
                    `
                    select 
                        m.*
                        ,t.compoundId as targetCompoundId
                        ,t.ionMech as targetIonMech
                        ,t.formula as targetFormula
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
                let sampleItems = rootGetters['sample/item/selectedRows'];
                let targetIsotopesSelected = selected ?
                    rootGetters['target/isotope/selectedRows']
                    : rootState.target.isotope.rows;
                return table.query(
                    `
                    select 
                        m.*
                        ,t.ionId as targetIonId
                        ,t.relAbu as targetRelAbu
                        ,t.mz as targetMz
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