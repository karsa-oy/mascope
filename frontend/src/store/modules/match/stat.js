import table from '$lib/table';

export default {
    namespaced: true,
    getters: {
        rows: (state, getters, rootState, rootGetters) =>
            ({ level = 'compound', selected = true }) => {
                let getRatedMatches = rootGetters['match/rating/rows'];
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
                    { matches: getRatedMatches({ level, selected }) }
                );
            },
    }
}