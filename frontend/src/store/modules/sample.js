import { dispatch, make } from 'vuex-pathify';

const state = {
    active: null,
    // matches
    matched: null,
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
        async load({ rootState, commit, dispatch }, sample) {
            // reset if previous sample loaded
            if (state.active) {
                dispatch('unload');
            }
            const sampleItemId = sample.sample_item_id;
            rootState.api.emit('subscribe', sampleItemId);
            // set sample active
            await commit('SET_ACTIVE', sample);
            await dispatch('loadMatches');
        },
        async loadMatches({ rootState, rootGetters, state, commit }) {
            const sampleItemId = state.active.sample_item_id;
            await rootState.api.query(`--sql
                -- matches exist
                SELECT
                    CASE
                        WHEN COUNT(sample_item_id) > 0 THEN 1
                        ELSE 0
                    END AS matched
                FROM match
                WHERE sample_item_id == '${sampleItemId}'
            `).then((res) => {
                commit('SET_MATCHED', res[0].matched);
            });
            const sampleBatchId = state.active.sample_batch_id;
            // initialize match filter
            const filterParams = rootGetters["batch/filterParams"];
            const mzTolerance = filterParams.mz_tolerance;
            const isotopeRatioTolerance = filterParams.isotope_ratio_tolerance;
            const peakMinIntensity = filterParams.peak_min_intensity;
            const peakMinSeparation = filterParams.peak_min_separation;
            const minIsotopeAbundance = filterParams.min_isotope_abundance;
            const minIsotopeCorrelation = filterParams.min_isotope_correlation;
            await rootState.api.query(`--sql
                -- matches
                DROP TABLE IF EXISTS sample_match_filter;
                CREATE TEMPORARY TABLE sample_match_filter AS
                    SELECT
                        CASE
                        -- set match_score to 0 if not within set tolerances
                            WHEN (
                                ABS(match_mz_error) <= ${mzTolerance}
                                AND ABS(match_abundance_error) <= ${isotopeRatioTolerance}
                                AND MAX(match_isotope_correlation, 0) > ${minIsotopeCorrelation}
                                AND sample_peak_area >= ${peakMinIntensity}
                                ) THEN match_score
                            ELSE 0
                        END AS match_score,
                        match_mz_error,
                        match_abundance_error,
                        match_isotope_correlation,
                        sample_item_id,
                        CASE
                            WHEN (
                                ABS(match_mz_error) <= ${mzTolerance}
                                AND ABS(match_abundance_error) <= ${isotopeRatioTolerance}
                                AND MAX(match_isotope_correlation, 0) > ${minIsotopeCorrelation}
                                )
                            THEN sample_peak_area
                            ELSE 0
                        END AS sample_peak_area,
                        sample_peak_area_relative,
                        sample_peak_mz,
                        sample_peak_tof,
                        sample_peak_interference,
                        mz,
                        relative_abundance,
                        target_collection_id,
                        target_collection_name,
                        target_collection_description,
                        target_compound_formula,
                        target_compound_id,
                        target_compound_name,
                        target_ion_formula,
                        target_ion_id,
                        target_isotope_id
                        ,2 as selection
                    FROM match
                    NATURAL LEFT JOIN match_interference
                    NATURAL LEFT JOIN target_isotope
                    NATURAL LEFT JOIN target_ion
                    NATURAL LEFT JOIN target_compound
                    NATURAL LEFT JOIN target_compound_in_target_collection
                    NATURAL LEFT JOIN target_collection
                    NATURAL LEFT JOIN target_collection_in_sample_batch
                    WHERE (
                        sample_batch_id == '${sampleBatchId}' 
                        AND sample_item_id == '${sampleItemId}'
                        AND relative_abundance >= ${minIsotopeAbundance}
                    )
            `);
            // load matches
            await rootState.api.query(`--sql
                SELECT
                    target_collection_id,
                    target_collection_name,
                    target_collection_description,
                    IFNULL(MAX(match_score), 0) AS match_score,
                    IFNULL(SUM(sample_peak_area_sum), 0) AS sample_peak_area_sum,
                    MAX(sample_peak_interference_max) AS sample_peak_interference_max
                FROM (
                    SELECT
                    sample_item_id,
                    target_collection_id,
                    target_collection_name,
                    target_collection_description,
                    MAX(match_score) as match_score,
                    SUM(sample_peak_area_sum) AS sample_peak_area_sum,
                    MAX(sample_peak_interference_sum) AS sample_peak_interference_max
                    FROM (
                        SELECT
                            sample_item_id,
                            target_ion_id,
                            target_compound_id,
                            target_collection_id,
                            target_collection_name,
                            target_collection_description,
                            SUM(match_score*relative_abundance) AS match_score,
                            SUM(sample_peak_area) AS sample_peak_area_sum,
                            SUM(sample_peak_interference) AS sample_peak_interference_sum
                        FROM sample_match_filter
                        GROUP BY sample_item_id, target_collection_id, target_compound_id, target_ion_id
                    )
                    GROUP BY sample_item_id, target_collection_id
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
                    IFNULL(SUM(sample_peak_area_sum), 0) AS sample_peak_area_sum,
                    MAX(sample_peak_interference_sum) AS sample_peak_interference_max
                FROM (
                    SELECT
                        sample_item_id,
                        target_ion_id,
                        target_compound_id,
                        target_compound_formula,
                        target_compound_name,
                        target_collection_id,
                        SUM(match_score*relative_abundance) AS match_score,
                        SUM(sample_peak_area) AS sample_peak_area_sum,
                        SUM(sample_peak_interference) AS sample_peak_interference_sum
                    FROM sample_match_filter
                    GROUP BY sample_item_id, target_collection_id, target_compound_id, target_ion_id
                )
                GROUP BY sample_item_id, target_collection_id, target_compound_id;
            `).then((res) => {
                commit('SET_MATCH_COMPOUNDS', res);
            });
            await rootState.api.query(`--sql
                SELECT
                    sample_item_id,
                    target_ion_formula,
                    target_ion_id,
                    target_compound_id,
                    target_collection_id,
                    IFNULL(SUM(match_score*relative_abundance), 0) AS match_score,
                    IFNULL(SUM(sample_peak_area), 0) AS sample_peak_area_sum,
                    SUM(sample_peak_interference) AS sample_peak_interference_sum
                FROM sample_match_filter
                GROUP BY sample_item_id, target_collection_id, target_compound_id, target_ion_id;
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
                    sample_peak_area,
                    sample_peak_area_relative,
                    sample_peak_mz,
                    sample_peak_tof,
                    sample_peak_interference,
                    target_isotope_id,
                    target_ion_id,
                    target_ion_formula,
                    target_compound_id,
                    target_collection_id,
                    target_compound_name,
                    target_compound_formula
                FROM sample_match_filter
            `).then((res) => {
                commit('SET_MATCH_ISOTOPES', res);
            });
        },
        async unload({ rootState, state, commit, dispatch }) {
            if (!state.active) return;
            rootState.api.emit('unsubscribe', state.active.sample_item_id);
            commit('SET_ACTIVE', null);
            // matches
            commit('SET_MATCHED', null);
            commit('SET_MATCH_COLLECTIONS', null);
            commit('SET_MATCH_COMPOUNDS', null);
            commit('SET_MATCH_IONS', null);
            commit('SET_MATCH_ISOTOPES', null);
            // calibration
            dispatch("calibration/unload", null, {root:true});
        },
        async reload({ rootGetters, dispatch, state }, sample=null) {
            const sampleToLoad = sample ? sample : state.active;
            if (sampleToLoad) {
                const sampleToLoadId = sampleToLoad.sample_item_id;
                await dispatch('unload');
                const activeSample = rootGetters["batch/sampleItem"](sampleToLoadId);
                dispatch('load', activeSample);
            }
        },
        async onSampleBatchExportPeaksFailed({dispatch}, error) {
            await dispatch(
                'app/pushNotification',
                {message: error, key: Math.random()}, 
                {root:true}
            );
        },
        async onSampleBatchExportPeaksReady({dispatch}) {
            await dispatch(
                'app/pushNotification',
                {message: "Sample batch peak export finished", key: Math.random()}, 
                {root:true}
            );
        },
        async onSampleItemCreated({ rootGetters, dispatch }, sample_item_id) {
            await dispatch('batch/onSampleBatchReload', null, {root:true});
            const sample_item = rootGetters['batch/sampleItem'](sample_item_id);
            await dispatch("load", sample_item);
        },
    },
    getters: {}
}