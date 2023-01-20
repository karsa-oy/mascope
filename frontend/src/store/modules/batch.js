import { dispatch, make } from 'vuex-pathify';
import { camelToSnakeCase } from '../../lib/util';

const state = {
    active: null,
    // calibration
    mzCalibration: null,
    // samples
    sampleItems: null,
    // targets
    targetCollections: null,
    targetCompounds: null,
    targetIons: null,
    targetIsotopes: null,
    // matches
    matchCollections: null,
    matchCompounds: null,
    matchIons: null,
    // build parameters
    paramCalibrationCollection: null,
    paramIonMechanisms: null,
    // filter parameters
    paramIsotopeRatioTolerance: null,
    paramMinIsotopeAbundance: null,
    paramMinIsotopeCorrelation: null,
    paramMzTolerance: null,
    paramPeakMinIntensity: null,
    paramPeakMinSeparation: null,
    paramPossibleMatchThreshold: null,
    paramProbableMatchThreshold: null,
}

const paramDefaults = {
    // build parameters
    paramCalibrationCollection: [],
    paramIonMechanisms: [],
    // filter parameters
    paramIsotopeRatioTolerance: 0.1,
    paramMinIsotopeAbundance: 0.15,
    paramMinIsotopeCorrelation: 0.6,
    paramMzTolerance: 15,
    paramPeakMinIntensity: null,
    paramPeakMinSeparation: null,
    paramPossibleMatchThreshold: 0.7,
    paramProbableMatchThreshold: 0.8,
}

// initialize parameter values in state with defaults
for (const field in state) {
    if (field.startsWith('param')) {
        state[field] = paramDefaults[field];
    }
}

export default {
    namespaced: true,
    state,
    mutations: {
        ...make.mutations(state),
    },
    actions: {
        // data loading
        async initMatchFilter({ rootState, state, getters }) {
            const batchId = state.active.sample_batch_id;
            // initialize match filter
            const filterParams = getters['filterParams'];
            const mzTolerance = filterParams.mz_tolerance;
            const isotopeRatioTolerance = filterParams.isotope_ratio_tolerance;
            const peakMinIntensity = filterParams.peak_min_intensity;
            const minIsotopeAbundance = filterParams.min_isotope_abundance;
            const minIsotopeCorrelation = filterParams.min_isotope_correlation
                ? filterParams.min_isotope_correlation
                : paramDefaults.paramMinIsotopeCorrelation;
            await rootState.api.query(`--sql
                -- matches
                DROP TABLE IF EXISTS batch_match_filter;
                CREATE TEMPORARY TABLE batch_match_filter AS
                    SELECT
                    *
                    FROM (
                        SELECT
                            filename,
                            relative_abundance,
                            sample_item_id,
                            sample_item_name,
                            sample_item_type,
                            target_compound_formula,
                            target_compound_id,
                            target_compound_name,
                            target_ion_formula,
                            target_ion_id,
                            ionization_mechanism AS target_ion_mechanism,
                            target_isotope_id,
                            sample_peak_interference,
                            CASE
                                WHEN (
                                    ABS(match_mz_error) <= ${mzTolerance}
                                    AND ABS(match_abundance_error) <= ${isotopeRatioTolerance}
                                    AND MAX(match_isotope_correlation, 0) >= ${minIsotopeCorrelation}
                                    AND ABS(match_abundance_error) <= ${isotopeRatioTolerance}
                                    AND relative_abundance >= ${minIsotopeAbundance}
                                    )
                                THEN sample_peak_area
                                ELSE 0
                            END AS sample_peak_area,
                            CASE
                                WHEN (
                                    ABS(match_mz_error) <= ${mzTolerance}
                                    AND ABS(match_abundance_error) <= ${isotopeRatioTolerance}
                                    AND MAX(match_isotope_correlation, 0) >= ${minIsotopeCorrelation}
                                    AND sample_peak_area >= ${peakMinIntensity}
                                    AND relative_abundance >= ${minIsotopeAbundance}
                                    )
                                THEN match_score
                                ELSE 0
                            END AS match_score
                        FROM sample_item
                        NATURAL LEFT JOIN sample_batch
                        NATURAL LEFT JOIN match
                        NATURAL LEFT JOIN match_interference
                        NATURAL LEFT JOIN target_isotope
                        NATURAL LEFT JOIN target_ion
                        NATURAL LEFT JOIN ionization_mechanism
                        NATURAL LEFT JOIN target_compound
                        WHERE (
                            sample_batch_id == '${batchId}'
                        )
                    )
            `);
        },
        async load({ rootState, state, commit, dispatch }, batch) {
            if (state.active) await dispatch('unload');
            const batchId = batch.sample_batch_id;
            rootState.api.emit('subscribe', batchId);
            // set batch active
            await commit('SET_ACTIVE', batch);
            // unpack parameters
            await dispatch('unpackParams');
            await dispatch('loadCalibration');
            await dispatch('loadTargets');
            await dispatch('loadSamples');
            await dispatch('loadMatches');
        },
        async loadCalibration({ rootState, commit }) {
            const calibrationFilename = state.active.calibration_sample_filename;
            await rootState.api.query(`--sql
                -- calibration
                SELECT
                    mz_calibration
                FROM sample_file
                WHERE filename == '${calibrationFilename}'
            `).then((res) => {
                if (res.length) commit('SET_MZ_CALIBRATION', res[0].mz_calibration);
            });
        },
        async loadMatches({ rootState, commit }) {
            // load matches
            await rootState.api.query(`--sql
                SELECT
                    filename,
                    sample_item_id,
                    sample_item_name,
                    MAX(match_score) AS match_score,
                    SUM(sample_peak_area_sum) AS sample_peak_area_sum
                FROM (
                    SELECT
                        filename,
                        sample_item_id,
                        sample_item_name,
                        target_ion_id,
                        target_compound_id,
                        SUM(match_score*relative_abundance) AS match_score,
                        SUM(sample_peak_area) AS sample_peak_area_sum
                    FROM batch_match_filter
                    GROUP BY sample_item_id, target_compound_id, target_ion_id
                )
                GROUP BY sample_item_id
            `).then((res) => {
                commit('SET_MATCH_COLLECTIONS', res);
            });
            await rootState.api.query(`--sql
                SELECT
                    filename,
                    sample_item_id,
                    sample_item_name,
                    sample_item_type,
                    target_compound_formula,
                    target_compound_id,
                    target_compound_name,
                    IFNULL(MAX(match_score), 0) as match_score,
                    IFNULL(SUM(sample_peak_area_sum), 0) AS sample_peak_area_sum,
                    MAX(sample_peak_interference_sum) AS sample_peak_interference_max
                FROM (
                    SELECT
                        filename,
                        sample_item_id,
                        sample_item_name,
                        sample_item_type,
                        target_compound_formula,
                        target_compound_id,
                        target_compound_name,
                        target_ion_id,
                        SUM(match_score*relative_abundance) AS match_score,
                        SUM(sample_peak_area) AS sample_peak_area_sum,
                        SUM(sample_peak_interference) AS sample_peak_interference_sum
                    FROM batch_match_filter
                    GROUP BY sample_item_id, target_compound_id, target_ion_id
                )
                GROUP BY sample_item_id, target_compound_id;
            `).then((res) => {
                commit('SET_MATCH_COMPOUNDS', res);
            });
            await rootState.api.query(`--sql
                SELECT
                    filename,
                    sample_item_id,
                    sample_item_name,
                    sample_item_type,
                    target_compound_formula,
                    target_compound_id,
                    target_compound_name,
                    target_ion_formula,
                    target_ion_mechanism,
                    IFNULL(SUM(match_score*relative_abundance), 0) AS match_score,
                    IFNULL(SUM(sample_peak_area), 0) AS sample_peak_area_sum,
                    SUM(sample_peak_interference) AS sample_peak_interference_sum
                FROM batch_match_filter
                GROUP BY sample_item_id, target_compound_id, target_ion_id;
            `).then((res) => {
                commit('SET_MATCH_IONS', res);
            });
        },
        async loadSamples({ rootState, commit, dispatch }) {
            // initialize match filter
            await dispatch('initMatchFilter');
            const batchId = state.active.sample_batch_id;
            // initialize sample filter
            await rootState.api.query(`--sql
                -- samples
                DROP TABLE IF EXISTS sample_item_filter;
                CREATE TEMPORARY TABLE sample_item_filter AS
                    SELECT
                        sample_item_id
                    FROM sample_item
                    WHERE sample_batch_id == '${batchId}'
            `);
            // load sample items
            const sampleItemActiveId = rootState.sample.active
                ? rootState.sample.active.sample_item_id
                : null;
            await rootState.api.query(`--sql
                SELECT
                    sample_item_id,
                    sample_item_name,
                    sample_item_attributes,
                    sample_item_type,
                    sample_batch_id,
                    sample_file_id,
                    filter_id,
                    datetime,
                    datetime_utc,
                    filename,
                    instrument,
                    length,
                    range,
                    mz_calibration,
                    sample_item_utc_created,
                    sample_item_utc_modified,
                    CASE
                        WHEN (
                            match_score IS NULL
                        ) THEN 0
                        ELSE 1
                    END AS matched,
                    IFNULL(MAX(match_score), 0) AS match_score,
                    IFNULL(SUM(sample_peak_area_sum), 0) AS sample_peak_area_sum,
                    sample_peak_interference_sum,
                    CASE
                        WHEN (
                            sample_item_id == '${sampleItemActiveId}'
                        ) THEN 3
                        ELSE 0
                    END AS selection
                FROM (
                    -- ion level
                    SELECT
                        sample_item_id,
                        target_ion_id,
                        target_compound_id,
                        SUM(match_score*relative_abundance) AS match_score,
                        SUM(sample_peak_area) AS sample_peak_area_sum,
                        SUM(sample_peak_interference) AS sample_peak_interference_sum
                    FROM (
                        -- isotope level
                        SELECT
                            sample_item_id,
                            match_score,
                            relative_abundance,
                            sample_peak_area,
                            sample_peak_interference,
                            target_isotope_id,
                            target_ion_id,
                            target_compound_id
                        FROM
                            sample_item_filter
                        NATURAL LEFT JOIN batch_match_filter
                    )
                    GROUP BY sample_item_id, target_compound_id, target_ion_id
                )
                NATURAL LEFT JOIN sample_item
                NATURAL LEFT JOIN sample_file
                GROUP BY sample_item_id
                ORDER BY sample_item_utc_created ASC
            `).then((res) => {
                commit('SET_SAMPLE_ITEMS', res);
            });
        },
        async loadTargets({ rootState, state, commit }) {
            const batchId = state.active.sample_batch_id;
            // initialize target collection filter
            await rootState.api.query(`--sql
                DROP TABLE IF EXISTS target_collection_filter;
                CREATE TEMPORARY TABLE target_collection_filter AS
                    SELECT
                        target_collection_id
                        ,0 as selection
                    FROM target_collection
                    NATURAL JOIN target_collection_in_sample_batch
                    WHERE sample_batch_id == '${batchId}'
            `);
            // load target collections
            await rootState.api.query(`--sql
                SELECT
                    target_collection_id,
                    target_collection_name,
                    target_collection_description,
                    selection
                FROM target_collection_filter
                NATURAL LEFT JOIN target_collection
            `).then((res) => {
                commit('SET_TARGET_COLLECTIONS', res);
            });
            // initialize target compound filter
            await rootState.api.query(`--sql
                DROP TABLE IF EXISTS target_compound_filter;
                CREATE TEMPORARY TABLE target_compound_filter AS
                    SELECT
                        target_compound_id,
                        target_collection_id
                        ,0 as selection
                    FROM target_compound
                    NATURAL JOIN target_compound_in_target_collection
                    NATURAL JOIN target_collection_in_sample_batch
                    WHERE sample_batch_id == '${batchId}'
            `);
            // load target compounds
            await rootState.api.query(`--sql
                SELECT
                    target_compound_id,
                    target_compound_name,
                    target_compound_formula,
                    target_collection_id,
                    cas_number,
                    selection
                FROM target_compound_filter
                NATURAL LEFT JOIN target_compound
            `).then((res) => {
                commit('SET_TARGET_COMPOUNDS', res);
            });
            // initialize target ion filter           
            await rootState.api.query(`--sql
                DROP TABLE IF EXISTS target_ion_filter;
                CREATE TEMPORARY TABLE target_ion_filter AS
                SELECT
                    target_ion_id,
                    target_ion_formula,
                    target_compound_id,
                    target_collection_id,
                    ionization_mechanism_id,
                    ionization_mechanism
                    ,0 as selection
                FROM (
                    SELECT
                    *
                    FROM
                        target_ion
                    NATURAL LEFT JOIN ionization_mechanism
                    WHERE ionization_mechanism_id IN (
                        ${`'`+state.active.build_params.ion_mechanisms.join(`','`)+`'`}
                    )
                )
                NATURAL JOIN target_compound_filter;
            `);
            // load target ions
            await rootState.api.query(`--sql
                SELECT
                    *
                FROM target_ion_filter
            `).then((res) => {
                commit('SET_TARGET_IONS', res);
            });
            
            // load target isotopes
            await rootState.api.query(`--sql
                SELECT
                    target_isotope.*,
                    selection
                FROM target_isotope
                NATURAL JOIN target_ion_filter
            `).then((res) => {
                commit('SET_TARGET_ISOTOPES', res);
            });
        },
        async reload({ rootGetters, getters, rootState, state, dispatch }, batch=null) {
            const batchToLoad = batch ? batch : state.active;
            if (batchToLoad) {
                const batchToLoadId = batchToLoad.sample_batch_id;
                const activeSample = rootState.sample.active;
                await dispatch('unload', false);
                const activeBatch = rootGetters["workspace/sampleBatch"](batchToLoadId);
                await dispatch('load', activeBatch);
                if (activeSample) {
                    const sample = getters['sampleItem'](activeSample.sample_item_id);
                    sample.selection = 3;
                    await dispatch('sample/reload', sample, {root:true});
                }
            }
        },
        async unload({ rootState, commit, dispatch }, propagate=true) {
            if (!state.active) return;
            rootState.api.emit('unsubscribe', state.active.sample_batch_id);
            commit('SET_ACTIVE', null);
            // calibration
            commit('SET_MZ_CALIBRATION', null);
            // parameters
            dispatch('resetParams');
            // samples
            commit('SET_SAMPLE_ITEMS', null);
            // targets
            commit('SET_TARGET_COLLECTIONS', null);
            commit('SET_TARGET_COMPOUNDS', null);
            commit('SET_TARGET_IONS', null);
            commit('SET_TARGET_ISOTOPES', null);
            // matches
            commit('SET_MATCH_COLLECTIONS', null);
            commit('SET_MATCH_COMPOUNDS', null);
            commit('SET_MATCH_IONS', null);
            if (propagate) dispatch("sample/unload", null, {root:true});
        },

        // parameters
        async resetParams({ state, commit }) {
            // reset parameters to default values
            for (const field in state) {
                if (field.startsWith('param')) {
                    const defaultValue = paramDefaults[field];
                    commit(`SET_${camelToSnakeCase(field).toUpperCase()}`, defaultValue);
                }
            }
        },
        async unpackParams({ state, commit }) {
            // unpack parameters from batch object into state variables
            const buildParams = state.active.build_params;
            for (const param in buildParams) {
                await commit(`SET_PARAM_${param.toUpperCase()}`, buildParams[param]);
            }
            const filterParams = state.active.filter_params;
            for (const param in filterParams) {
                await commit(`SET_PARAM_${param.toUpperCase()}`, filterParams[param]);
            }
        },

        // backend notifications
        async onSampleBatchReload({ dispatch }) {
            await dispatch('api/reloadDb', null, {root:true})
                .then(() => dispatch('reload'));
        },

        // selection
        async batchToggle({ rootState, state, dispatch }, batch) {
            rootState.workspace.batches.forEach(
                (row) => row.selection = 0
                );
            const active_batch_id = state.active
                ? state.active.sample_batch_id
                : null;
            if (active_batch_id == batch.sample_batch_id) {
                dispatch('unload');
            } else {
                dispatch('load', batch);
                rootState.workspace.batches.filter(
                    (row) => row.sample_batch_id == batch.sample_batch_id)
                    .forEach((row) => row.selection = 2);
            }
        },
        // Sample selection toggling
        async sampleItemFocus({ dispatch, getters, state }, sampleItemFocused) {
            const sampleItemFocusedId = sampleItemFocused.sample_item_id;
            state.sampleItems.filter(
                (row) => row.sample_item_id != sampleItemFocusedId
                    && row.selection == 3
                )
                .forEach((item) => item.selection = 0);
            sampleItemFocused = getters['sampleItem'](sampleItemFocusedId);
            switch (sampleItemFocused.selection) {
                case 0:
                case 2:
                    // Focus
                    sampleItemFocused.selection = 3;
                    await dispatch("sample/load", sampleItemFocused, {root:true})
                    break;
                case 3:
                    // Unfocus
                    sampleItemFocused.selection = 0;
                    await dispatch("sample/unload", null, {root:true})
                    break;
                }
        },
        async sampleItemToggle({ getters, state }, sampleItemToggled) {
            const sampleItemToggledId = sampleItemToggled.sample_item_id;
            state.sampleItems.filter(
                (row) => row.sample_item_id != sampleItemToggledId
                    && row.selection == 2
                )
                .forEach((item) => item.selection = 0);
            sampleItemToggled = getters['sampleItem'](sampleItemToggledId);
            switch (sampleItemToggled.selection) {
                case 0:
                    // Select
                    sampleItemToggled.selection = 2;
                    break;
                case 2:
                    // Unselect
                    sampleItemToggled.selection = 0;
                    break;
                case 3:
                    // Stay focused
                    sampleItemToggled.selection = 3;
                    break;
                }
        },
        async targetCollectionToggle({ getters, state }, targetCollectionToggled) {
            const targetCollectionToggledId = targetCollectionToggled.target_collection_id;
            state.targetCollections.filter(
                (row) => row.target_collection_id != targetCollectionToggledId
                    && row.selection == 2
                )
                .forEach((collection) => collection.selection = 0);
                targetCollectionToggled = getters['targetCollection'](targetCollectionToggledId);
            switch (targetCollectionToggled.selection) {
                case 0:
                    // Select
                    targetCollectionToggled.selection = 2;
                    break;
                case 2:
                    // Unselect
                    targetCollectionToggled.selection = 0;
                    break;
                case 3:
                    // Stay focused
                    targetCollectionToggled.selection = 3;
                    break;
                }
        },
    },
    getters: {
        buildParams: (state) => {
            return {
                'calibration_collection': state.paramCalibrationCollection,
                'ion_mechanisms': state.paramIonMechanisms,
            };
        },
        filterParams: (state) => {
            return {
                'isotope_ratio_tolerance': state.paramIsotopeRatioTolerance,
                'min_isotope_abundance': state.paramMinIsotopeAbundance,
                'min_isotope_correlation': state.paramMinIsotopeCorrelation,
                'mz_tolerance': state.paramMzTolerance,
                'peak_min_intensity': state.paramPeakMinIntensity,
                'peak_min_separation': state.paramPeakMinSeparation,
                'possible_match_threshold': state.paramPossibleMatchThreshold,
                'probable_match_threshold': state.paramProbableMatchThreshold,
            };
        },
        // get all rows as proxy array
        sampleItems: (state) => {
            return state.sampleItems
                ? state.sampleItems
                : [];
        },
        targetCollections: (state) => {
            return state.targetCollections
                ? state.targetCollections
                : [];
        },
        targetCompounds: (state) => {
            return state.targetCompounds
                ? state.targetCompounds
                : [];
        },
        targetIons: (state) => {
            return state.targetIons
                ? state.targetIons
                : []
        },
        targetIsotopes: (state) => {
            return state.targetIsotopes
                ? state.targetIsotopes
                : [];
        },
        // get row from id
        sampleItem: (state, getters) => (sampleItemId) => {
            const [sampleItem] = getters['sampleItems']
                .filter((row) => (row.sample_item_id == sampleItemId));
            return sampleItem ?? null;
        },
        targetCollection: (state, getters) => (targetCollectionId) => {
            const [targetCollection] = getters['targetCollections']
                .filter((row) => (row.target_collection_id == targetCollectionId));
            return targetCollection ?? null;
        },
        targetCompound: (state, getters) => (targetCompoundId) => {
            const [targetCompound] = getters['targetCompounds']
                .filter((row) => (row.target_compound_id == targetCompoundId));
            return targetCompound ?? null;
        },
        targetIon: (state, getters) => (targetIonId) => {
            const [targetIon] = getters['targetIons']
                .filter((row) => (row.target_ion_id == targetIonId));
            return targetIon ?? null;
        },
        targetIsotope: (state, getters) => (targetIsotopeId) => {
            const [targetIsotope] = getters['targetIsotopes']
                .filter((row) => (row.target_isotope_id == targetIsotopeId));
            return targetIsotope ?? null;
        },
        // get selected
        sampleItemsSelected: (state, getters) => {
            return getters['sampleItems']
                .filter((sampleItem) => sampleItem.selection >= 2);
        },
        sampleItemFocused: (state, getters) => {
            const sampleItem = getters['sampleItems']
                .filter((sampleItem) => sampleItem.selection == 3);
            return sampleItem[0] ?? null
        },
        targetCollectionsSelected: (state, getters) => {
            return getters['targetCollections']
                .filter((row) => row.selection >= 2);
        },
        targetCompoundsSelected: (state, getters) => {
            return getters['targetCompounds']
                .filter((row) => row.selection >= 2);
        },
        targetIonsSelected: (state, getters) => {
            return getters['targetIonsSelected']
                .filter((row) => row.selection >= 2);
        },
        targetIsotopesSelected: (state, getters) => {
            return getters['targetIsotopes']
                .filter((row) => row.selection >= 2);
        },
    }
}