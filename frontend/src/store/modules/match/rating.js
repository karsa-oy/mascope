import table from '$lib/table';

export default {
    namespaced: true,
    getters: {
        rows: (state, getters, rootState, rootGetters) =>
            ({ level = 'compound', selected = true }) => {
                let param = rootState.match.param;
                let getJoinedMatches = rootGetters['match/join/rows'];
                let ratings = table.query(
                    `
                    select
                        m.*
                        ,(case
                            when matchScore >= ${param.probableMatchThreshold}
                                then 'probable'
                            when matchScore < ${param.probableMatchThreshold}
                                and matchScore >= ${param.possibleMatchThreshold}
                                then 'possible'
                            when matchScore < ${param.possibleMatchThreshold}
                                then 'improbable'
                            else 'unknown'
                        end) as rating
                    from matches m
                    ` ,
                    { matches: getJoinedMatches({ level, selected }) }
                );
                let compounds = rootState.target.compound.rows;
                let ions = rootState.target.ion.rows;
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
    }
}