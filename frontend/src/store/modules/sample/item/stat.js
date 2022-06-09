import table from "$lib/table";

function toTitleCase(string) {
    return string[0].toUpperCase() + string.substring(1).toLowerCase();
}

export default {
    namespaced: true,
    getters: {
        rows: (state, getters, rootState, rootGetters) =>
            ({ level = 'compound', selected = true }) => {
                let sampleItem = rootState.sample.item;
                let targetLevel = 'target' + toTitleCase(level);
                let matchLevel = 'match' + toTitleCase(level);
                let matches = rootGetters['match/rating/rows']({ level, selected });
                let samples = selected ? rootGetters['sample/item/selectedRows'] : sampleItem.rows;
                let total = table.query(
                    `
                    select
                        m.sampleItemId as id
                        ,count(distinct m.${targetLevel}Id) as ${matchLevel}TotalCount
                    from matches m
                    group by m.sampleItemId
                    `, { matches }
                );
                let probable = table.query(
                    `
                    select
                        m.sampleItemId as id
                        ,count(distinct m.${targetLevel}Id) as ${matchLevel}ProbableCount
                    from matches m
                    where rating = 'probable'
                    group by m.sampleItemId
                    `, { matches }
                );
                let possible = table.query(
                    `
                    select
                        m.sampleItemId as id
                        ,count(distinct m.${targetLevel}Id) as ${matchLevel}PossibleCount
                    from matches m
                    where rating = 'possible'
                    group by m.sampleItemId
                    `, { matches }
                );
                let result = table.query(
                    `
                    select
                        samp.*
                        ,coalesce(tot.${matchLevel}TotalCount, 0) as ${matchLevel}TotalCount
                        ,coalesce(prob.${matchLevel}ProbableCount, 0) as ${matchLevel}ProbableCount
                        ,coalesce(poss.${matchLevel}PossibleCount, 0) as ${matchLevel}PossibleCount
                    from samples samp
                    left join total tot
                        on samp.id = tot.id
                    left join probable prob
                        on samp.id = prob.id
                    left join possible poss
                        on samp.id = poss.id
                    `, { samples, total, probable, possible }
                );
                if (rootState.dev.logGetters) console.table(result);
                return result;
            },
    }
}