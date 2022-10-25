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
    paramMinIsotopeAbundance: 0.05,
    paramMzTolerance: 10,
    paramPeakMinIntensity: null,
    paramPeakMinSeparation: null,
    paramPossibleMatchThreshold: 0.7,
    paramProbableMatchThreshold: 0.9,
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
        async initMatchFilter({ rootState, state, getters, commit }) {
            const batchId = state.active.sample_batch_id;
            // initialize match filter
            const filterParams = getters['filterParams'];
            const mzTolerance = filterParams.mz_tolerance;
            const isotopeRatioTolerance = filterParams.isotope_ratio_tolerance;
            const peakMinIntensity = filterParams.peak_min_intensity;
            const peakMinSeparation = filterParams.peak_min_separation;
            const minIsotopeAbundance = filterParams.min_isotope_abundance;
            await rootState.api.query(`--sql
                -- matches
                DROP TABLE IF EXISTS batch_match_filter;
                CREATE TEMPORARY TABLE batch_match_filter AS
                    SELECT
                        filename,
                        match_score,
                        relative_abundance,
                        sample_item_id,
                        sample_item_name,
                        sample_peak_height,
                        target_collection_id,
                        target_collection_name,
                        target_compound_formula,
                        target_compound_id,
                        target_compound_name,
                        target_ion_formula,
                        target_ion_id,
                        ionization_mechanism AS target_ion_mechanism,
                        target_isotope_id
                    FROM sample_item
                    NATURAL LEFT JOIN sample_batch
                    NATURAL LEFT JOIN target_collection_in_sample_batch
                    NATURAL LEFT JOIN target_collection
                    NATURAL LEFT JOIN target_compound_in_target_collection
                    NATURAL LEFT JOIN target_compound
                    NATURAL LEFT JOIN target_ion
                    NATURAL LEFT JOIN ionization_mechanism
                    NATURAL LEFT JOIN target_isotope
                    NATURAL LEFT JOIN match
                    WHERE (
                        sample_batch_id == '${batchId}'
                        AND ABS(match_mz_error) <= ${mzTolerance}
                        AND ABS(match_abundance_error) <= ${isotopeRatioTolerance}
                        AND sample_peak_height >= ${peakMinIntensity}
                        AND relative_abundance >= ${minIsotopeAbundance}
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
            // initialize match filter
            await dispatch('initMatchFilter');
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
                    SUM(sample_peak_height) AS sample_peak_height_sum
                FROM batch_match_filter
                GROUP BY sample_item_id
            `).then((res) => {
                commit('SET_MATCH_COLLECTIONS', res);
            });
            await rootState.api.query(`--sql
                SELECT
                    filename,
                    sample_item_id,
                    sample_item_name,
                    target_collection_name,
                    target_compound_formula,
                    target_compound_id,
                    target_compound_name,
                    target_ion_formula,
                    target_ion_mechanism,
                    AVG(match_score) AS match_score,
                    SUM(sample_peak_height) AS sample_peak_height_sum
                FROM batch_match_filter
                GROUP BY sample_item_id, target_compound_id, target_ion_id;
            `).then((res) => {
                commit('SET_MATCH_IONS', res);
            });
            await rootState.api.query(`--sql
                SELECT
                    filename,
                    sample_item_id,
                    sample_item_name,
                    target_collection_name,
                    target_compound_formula,
                    target_compound_id,
                    target_compound_name,
                    AVG(match_score) AS match_score,
                    SUM(sample_peak_height) AS sample_peak_height_sum
                FROM batch_match_filter
                GROUP BY sample_item_id, target_compound_id;
            `).then((res) => {
                commit('SET_MATCH_COMPOUNDS', res);
            });
        },
        async loadSamples({ rootState, commit }) {
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
                    datetime,
                    datetime_utc,
                    filename,
                    instrument,
                    length,
                    range,
                    mz_calibration,
                    sample_item_utc_created,
                    sample_item_utc_modified,
                    IFNULL(MAX(match_score), 0) AS match_score,
                    IFNULL(SUM(sample_peak_height_sum), 0) AS sample_peak_height_sum,
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
                        SUM(sample_peak_height) AS sample_peak_height_sum
                    FROM (
                        -- isotope level
                        SELECT
                            sample_item_id,
                            match_score,
                            relative_abundance,
                            sample_peak_height,
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
                        target_compound_id
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
                NATURAL LEFT JOIN target_compound_in_target_collection
            `).then((res) => {
                commit('SET_TARGET_COMPOUNDS', res);
            });
            // initialize target ion filter           
            await rootState.api.query(`--sql
                DROP TABLE IF EXISTS target_ion_filter;
                CREATE TEMPORARY TABLE target_ion_filter AS
                    SELECT
                        target_ion_id
                        ,0 as selection
                    FROM target_ion
                    NATURAL JOIN target_compound_in_target_collection
                    NATURAL JOIN target_collection_in_sample_batch
                    WHERE sample_batch_id == '${batchId}'
            `);
            // load target ions
            await rootState.api.query(`--sql
                SELECT
                    target_ion.*,
                    ionization_mechanism.*,
                    selection
                FROM target_ion_filter
                NATURAL LEFT JOIN target_ion
                NATURAL LEFT JOIN ionization_mechanism
                WHERE ionization_mechanism_id IN (
                    ${`'`+state.active.build_params.ion_mechanisms.join(`','`)+`'`}
                    )
            `).then((res) => {
                commit('SET_TARGET_IONS', res);
            });
            
            // initialize target isotope filter
            await rootState.api.query(`--sql
                -- targets
                DROP TABLE IF EXISTS target_isotope_filter;
                CREATE TEMPORARY TABLE target_isotope_filter AS
                    SELECT
                        target_isotope_id
                        ,0 as selection
                    FROM target_isotope
                    NATURAL JOIN target_ion
                    NATURAL JOIN target_compound_in_target_collection
                    NATURAL JOIN target_collection_in_sample_batch
                    WHERE (
                        sample_batch_id == '${batchId}'
                    )
            `);
            // load target isotopes
            await rootState.api.query(`--sql
                SELECT
                    target_isotope.*,
                    selection
                FROM target_isotope_filter
                NATURAL LEFT JOIN target_isotope
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
        async sampleItemFocus({ rootState, dispatch, getters, state }, sampleItemFocused) {
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
        async sampleItemToggle({ rootState, dispatch, getters, state }, sampleItemToggled) {
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