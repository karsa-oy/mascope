import { make } from 'vuex-pathify';

const state = {
    active: null,
    // matches
    matchCollections: null,
    matchCompounds: null,
    matchIons: null,
}

export default {
    namespaced: true,
    state,
    mutations: make.mutations(state),
    actions: {
        async load({ rootState, commit, dispatch }, sample) {
            const api = rootState.api;
            const sampleId = sample.sample_item_id;
            await dispatch('initFilters', sampleId);
            await commit('SET_ACTIVE', null);
            // load matches
            await api.query(`--sql
                SELECT
                    target_collection_id,
                    target_collection_name,
                    MAX(match_score) AS match_score,
                    SUM(sample_peak_height) AS sample_peak_height_sum
                FROM sample_match_filter
                GROUP BY sample_item_id, target_collection_id;
            `).then((res) => {
                commit('SET_MATCH_COLLECTIONS', res);
            });
            await api.query(`--sql
                SELECT
                    target_compound_formula,
                    sample_item_id,
                    target_collection_id,
                    target_compound_id,
                    target_compound_name,
                    MAX(match_score) AS match_score,
                    SUM(sample_peak_height) AS sample_peak_height_sum
                FROM sample_match_filter
                GROUP BY sample_item_id, target_compound_id;
            `).then((res) => {
                commit('SET_MATCH_COMPOUNDS', res);
            });
            await api.query(`--sql
                SELECT
                    sample_item_id,
                    target_ion_formula,
                    target_ion_id,
                    target_compound_id,
                    MAX(match_score) AS match_score,
                    SUM(sample_peak_height) AS sample_peak_height_sum
                FROM sample_match_filter
                GROUP BY sample_item_id, target_compound_id, target_ion_id;
            `).then((res) => {
                commit('SET_MATCH_IONS', res);
            });
            // set batch active
            await commit('SET_ACTIVE', sample);
        },
        async unload({ commit }) {
            commit('SET_ACTIVE', null);
            // matches
            commit('SET_MATCH_COLLECTIONS', null);
            commit('SET_MATCH_COMPOUNDS', null);
            commit('SET_MATCH_IONS', null);
        },
        async reload({ dispatch, state }) {
            if (state.active) {
                dispatch('load', state.active);
            }
        },
        // selection
        async initFilters({ rootState }, sampleId) {
            const api = rootState.api;
            await api.query(`--sql
                DROP TABLE IF EXISTS sample_match_filter;
            `);
            await api.query(`--sql
                -- matches
                CREATE TEMPORARY TABLE sample_match_filter AS
                    SELECT
                        match.*,
                        target_collection_id,
                        target_collection_name,
                        target_compound_formula,
                        target_compound_id,
                        target_compound_name,
                        target_ion_formula,
                        target_ion_id
                        ,2 as selection
                    FROM sample_item
                    NATURAL LEFT JOIN match
                    NATURAL LEFT JOIN target_isotope
                    NATURAL LEFT JOIN target_ion
                    NATURAL LEFT JOIN target_compound
                    NATURAL LEFT JOIN target_compound_in_target_collection
                    NATURAL LEFT JOIN target_collection
                    WHERE sample_item_id == '${sampleId}'
            `);
        },
    },
    getters: {}
}