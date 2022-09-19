import { make } from 'vuex-pathify';

const state = {
    active: null,
    // matches
    matchCollections: null,
    matchCompounds: null,
    matchIons: null,
    matchIsotopes: null,
}

export default {
    namespaced: true,
    state,
    mutations: make.mutations(state),
    actions: {
        async load({ commit, dispatch }, sample) {
            // set sample active
            await commit('SET_ACTIVE', sample);
            await dispatch('loadMatches');
        },
        async loadMatches({ rootState, state, commit }) {
            const sampleId = state.active.sample_item_id;
            // initialize match filter
            const filterParams = rootState.batch.active.filter_params;
            const mzTolerance = filterParams.mz_tolerance;
            const isotopeRatioTolerance = filterParams.isotope_ratio_tolerance;
            const peakMinIntensity = filterParams.peak_min_intensity;
            const peakMinSeparation = filterParams.peak_min_separation;
            const minIsotopeAbundance = filterParams.min_isotope_abundance;
            await rootState.api.query(`--sql
                -- matches
                DROP TABLE IF EXISTS sample_match_filter;
                CREATE TEMPORARY TABLE sample_match_filter AS
                    SELECT
                        match.*,
                        mz,
                        relative_abundance,
                        target_collection_id,
                        target_collection_name,
                        target_compound_formula,
                        target_compound_id,
                        target_compound_name,
                        target_ion_formula,
                        target_ion_id
                        ,2 as selection
                    FROM match
                    NATURAL LEFT JOIN target_isotope
                    NATURAL LEFT JOIN target_ion
                    NATURAL LEFT JOIN target_compound
                    NATURAL LEFT JOIN target_compound_in_target_collection
                    NATURAL LEFT JOIN target_collection
                    WHERE (sample_item_id == '${sampleId}'
                        AND ABS(match_mz_error) <= ${mzTolerance}
                        AND ABS(match_abundance_error) <= ${isotopeRatioTolerance}
                        AND sample_peak_height >= ${peakMinIntensity}
                        AND relative_abundance >= ${minIsotopeAbundance}
                    )
            `);
            // load matches
            await rootState.api.query(`--sql
                SELECT
                    target_collection_id,
                    target_collection_name,
                    IFNULL(MAX(match_score), 0) AS match_score,
                    IFNULL(SUM(sample_peak_height_sum), 0) AS sample_peak_height_sum
                FROM (
                    SELECT
                    sample_item_id,
                    target_collection_id,
                    target_collection_name,
                    MAX(match_score) as match_score,
                    SUM(sample_peak_height_sum) AS sample_peak_height_sum
                    FROM (
                        SELECT
                            sample_item_id,
                            target_ion_id,
                            target_compound_id,
                            target_collection_id,
                            target_collection_name,
                            SUM(match_score*relative_abundance) AS match_score,
                            SUM(sample_peak_height) AS sample_peak_height_sum
                        FROM sample_match_filter
                        GROUP BY sample_item_id, target_compound_id, target_ion_id
                    )
                )
                GROUP BY sample_item_id, target_collection_id;
            `).then((res) => {
                commit('SET_MATCH_COLLECTIONS', res);
            });
            await rootState.api.query(`--sql
                SELECT
                    sample_item_id,
                    target_compound_id,
                    target_compound_formula,
                    target_compound_name,
                    target_collection_id,
                    IFNULL(MAX(match_score), 0) as match_score,
                    IFNULL(SUM(sample_peak_height_sum), 0) AS sample_peak_height_sum
                FROM (
                    SELECT
                        sample_item_id,
                        target_ion_id,
                        target_compound_id,
                        target_compound_formula,
                        target_compound_name,
                        target_collection_id,
                        SUM(match_score*relative_abundance) AS match_score,
                        SUM(sample_peak_height) AS sample_peak_height_sum
                    FROM sample_match_filter
                    GROUP BY sample_item_id, target_compound_id, target_ion_id
                )
                GROUP BY sample_item_id, target_compound_id;
            `).then((res) => {
                commit('SET_MATCH_COMPOUNDS', res);
            });
            await rootState.api.query(`--sql
                SELECT
                    sample_item_id,
                    target_ion_formula,
                    target_ion_id,
                    target_compound_id,
                    IFNULL(SUM(match_score*relative_abundance), 0) AS match_score,
                    IFNULL(SUM(sample_peak_height), 0) AS sample_peak_height_sum
                FROM sample_match_filter
                GROUP BY sample_item_id, target_compound_id, target_ion_id;
            `).then((res) => {
                commit('SET_MATCH_IONS', res);
            });
            await rootState.api.query(`--sql
                SELECT
                    match_score,
                    match_mz_error,
                    mz,
                    relative_abundance,
                    sample_item_id,
                    sample_peak_height,
                    sample_peak_height_relative,
                    sample_peak_mz,
                    sample_peak_tof,
                    target_isotope_id,
                    target_ion_id,
                    target_ion_formula,
                    target_compound_id,
                    target_compound_name,
                    target_compound_formula
                FROM sample_match_filter
            `).then((res) => {
                commit('SET_MATCH_ISOTOPES', res);
            });
        },
        async unload({ commit }) {
            commit('SET_ACTIVE', null);
            // matches
            commit('SET_MATCH_COLLECTIONS', null);
            commit('SET_MATCH_COMPOUNDS', null);
            commit('SET_MATCH_IONS', null);
            commit('SET_MATCH_ISOTOPES', null);
        },
        async reload({ dispatch, state }) {
            if (state.active) {
                dispatch('load', state.active);
            }
        },
    },
    getters: {}
}