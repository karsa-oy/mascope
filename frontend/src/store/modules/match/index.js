import param from "./param";
import rating from "./rating";
import join from "./join";
import stat from "./stat";

import table from '$lib/table';

export default {
    namespaced: true,
    state: {
        collectionRows: [],
        compoundRows: [],
        ionRows: [],
        isotopeRows: [],
        sampleItems: [],
    },
    mutations: {
        LOAD(state, { matches, sampleItems }) {
            state.collectionRows.push(...matches.collection);
            state.compoundRows.push(...matches.compound);
            state.ionRows.push(...matches.ion);
            state.isotopeRows.push(...matches.isotope);
            state.sampleItems.push(...sampleItems);
        },
        UNLOAD(state, { sampleItems }) {
            let sampleItemIds = sampleItems.map(row => row.id);
            let rowsToKeep =
                (row) => !sampleItemIds.includes(row.sampleItemId)
            state.collectionRows = state.collectionRows
                .filter(rowsToKeep);
            state.compoundRows = state.compoundRows
                .filter(rowsToKeep);
            state.ionRows = state.ionRows
                .filter(rowsToKeep);
            state.isotopeRows = state.isotopeRows
                .filter(rowsToKeep);
            let sampleItemsToKeep =
                (item) => !sampleItemIds.includes(item.id)
            state.sampleItems = state.sampleItems
                .filter(sampleItemsToKeep);
        }
    },
    actions: {
        sync({ dispatch, state, rootGetters }) {
            // ensure missing matches are correctly 
            // syncronized with sample item selection
            // prepare sample items
            let sampleItemsLoaded = state
                .sampleItems;
            let sampleItemsSelected =
                rootGetters['sample/item/selectedRows'];
            // clear expired items
            let sampleItemsExpired = sampleItemsLoaded
                .filter(
                    // item expired if it is
                    // loaded but not selected
                    loaded => !sampleItemsSelected
                        .map(selected => selected.id)
                        .includes(loaded.id)
                );
            if (sampleItemsExpired.length > 0) {
                dispatch('clear', {
                    sampleItems: sampleItemsExpired
                });
            }
            // request missing items
            let sampleItemsMissing = sampleItemsSelected
                .filter(
                    // item missing if it is
                    // selected but not loaded
                    selected => !sampleItemsLoaded
                        .map(loaded => loaded.id)
                        .includes(selected.id)
                );
            if (sampleItemsMissing.length > 0) {
                dispatch('request', {
                    sampleItems: sampleItemsMissing
                });
            }
        },
        async request({ commit, rootState }, { sampleItems }) {
            let targetIsotopes = rootState.target.isotope.rows
            let getCompoundId = (ionId) => ({
                targetCompoundId: table.select(rootState.target.ion.rows, {
                    id: ionId
                })[0].targetCompoundId
            })
            let getCollectionId = (ionId) => ({
                targetCollectionId: table.select(rootState.target.compound.rows, {
                    id: getCompoundId(ionId).targetCompoundId
                })[0].targetCollectionId
            })
            if (targetIsotopes.length > 0 && sampleItems.length > 0) {
                targetIsotopes = targetIsotopes
                    .map((row) => ({
                        ...row,
                        ...getCompoundId(row.targetIonId),
                        ...getCollectionId(row.targetIonId)
                    }));
                // request matches
                let param = rootState.match.param;
                rootState.api.call({
                    endpoint: 'match_request',
                    onSuccess: async (response) => await commit('LOAD', response)
                }, ...sampleItems.map(
                    (sampleItem) => {
                        return {
                            requestId: table.genId(),
                            sampleItem,
                            targetIsotopes,
                            // match params
                            mzTolerance: param.mzTolerance,
                            isoAbuTolerance: param.isoRatioTolerance,
                            // peak params
                            mzRange: param.mzRange,
                            tRange: param.tRange,
                            minPeakIntensity: param.peakMinIntensity,
                            minPeakSeparation: param.peakMinSeparation,
                        }
                    }
                ));
            }
        },
        async clear({ commit }, { sampleItems }) {
            commit('UNLOAD', { sampleItems });
        },
    },
    getters: {
        exists: function (state) {
            let totalMatches = state.collectionRows.length
                + state.compoundRows.length
                + state.ionRows.length
                + state.isotopeRows.length
            return totalMatches > 0;
        },
    },
    watchers: {
        'sample/item/selectedRows': 'match/sync',
        'target/isotope/rows': 'match/sync'
    },
    modules: {
        param,
        rating,
        stat,
        join,
    }
}