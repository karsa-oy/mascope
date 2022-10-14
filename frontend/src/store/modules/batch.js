import { dispatch, make } from 'vuex-pathify';
import camelToSnakeCase from '../../lib/util';

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
                        match_score,
                        relative_abundance,
                        sample_item_id,
                        sample_peak_height,
                        target_collection_id,
                        target_collection_name,
                        target_compound_id,
                        target_ion_id,
                        target_isotope_id
                    FROM sample_item
                    NATURAL LEFT JOIN sample_batch
                    NATURAL LEFT JOIN target_collection_in_sample_batch
                    NATURAL LEFT JOIN target_collection
                    NATURAL LEFT JOIN target_compound_in_target_collection
                    NATURAL LEFT JOIN target_compound
                    NATURAL LEFT JOIN target_ion
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
            return
            // load matches
            await rootState.api.query(`--sql
                SELECT
                    sample_item_id,
                    MAX(match_score) AS match_score,
                    SUM(sample_peak_height) AS sample_peak_height_sum
                FROM batch_match_filter
                GROUP BY sample_item_id
            `).then((res) => {
                commit('SET_MATCH_COLLECTIONS', res);
            });
            await rootState.api.query(`--sql
                SELECT
                    sample_item_id,
                    target_compound_id,
                    AVG(match_score) AS match_score,
                    SUM(sample_peak_height) AS sample_peak_height_sum
                FROM batch_match_filter
                GROUP BY sample_item_id, target_compound_id, target_ion_id;
            `).then((res) => {
                commit('SET_MATCH_IONS', res);
            });
            await rootState.api.query(`--sql
                SELECT
                    sample_item_id,
                    target_compound_id,
                    AVG(match_score) AS match_score,
                    SUM(sample_peak_height) AS sample_peak_height_sum
                FROM batch_match_filter
                GROUP BY sample_item_id, target_compound_id;
            `).then((res) => {
                commit('SET_MATCH_COMPOUNDS', res);
            });
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
            // await dispatch('loadMatches');
            await dispatch('loadSamples');
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
            // initialize match filter
            await dispatch('batch/initMatchFilter', null, {root:true});
            // load sample items
            await rootState.api.query(`--sql
                SELECT
                    sample_item_id,
                    sample_item_name,
                    sample_item_description,
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
                    IFNULL(MAX(match_score), 0) AS match_score,
                    IFNULL(SUM(sample_peak_height_sum), 0) AS sample_peak_height_sum,
                    0 AS selection
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
            const sampleItemFocused = rootState.sample.active;
            if (sampleItemFocused) {
                dispatch('batch/sampleItemFocus', sampleItemFocused);
            }
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
                    config_mechanism.*,
                    selection
                FROM target_ion_filter
                NATURAL LEFT JOIN target_ion
                NATURAL LEFT JOIN config_mechanism
                WHERE mechanism_id IN (
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
        },
        async unload({ rootState, commit }) {
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
            // // unload sample
            // dispatch("sample/unload", null, {root:true})
        },
        async reload({ state, dispatch }) {
            if (state.active) {
                const activeBatch = {...state.active};
                await dispatch('unload');
                await dispatch('load', activeBatch);
                await dispatch('sample/reload', null, {root:true});

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
        async onSampleBatchUpdated({ dispatch }) {
            await dispatch('api/reloadDb', null, {root:true})
                .then(() => dispatch('reload'));
        },
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
        // selection
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
        // Target selection toggling actions
        // these retrieve toggled isotope selections and trigger the updateTargetFilter 
        // action which propagates these to up the hierarchy.
        async targetCollectionToggle({ rootState, dispatch, getters }, targetCollection) {
            return
            const api = rootState.api;
            const targetCollectionId = targetCollection.target_collection_id;
            // get updated selection
            const {
                nextOwnSelection,
                nextChildSelection,
                nextPeerSelection
            } = getters['targetCollectionNextSelection'](targetCollectionId);
            // save toggled isotopes and next selection in temp table
            if (nextPeerSelection == null) {
                await api.query(`--sql
                    CREATE TEMPORARY TABLE toggled_target_collection AS
                        SELECT
                            target_collection_id,
                            ${nextChildSelection} AS next_selection
                        FROM target_collection_filter
                        NATURAL JOIN target_ion
                        NATURAL JOIN target_compound_in_target_collection
                        WHERE target_collection_id == '${targetCollectionId}'
                `);
            } else {
                await api.query(`--sql
                    CREATE TEMPORARY TABLE toggled_target_collection AS
                        SELECT
                            target_isotope_id,
                            CASE
                                WHEN target_collection_id == '${targetCollectionId}' THEN ${nextChildSelection}
                                ELSE ${nextPeerSelection}
                            END AS next_selection
                        FROM target_isotope_filter
                        NATURAL JOIN target_ion
                        NATURAL JOIN target_compound_in_target_collection
                `);
            }
            // create focus clause
            const targetCollectionFocusClause = `--sql
                WHEN target_collection_id == '${targetCollectionId}' THEN ${nextOwnSelection}
            `
            dispatch('updateTargetFilters', { targetCollectionFocusClause });
        },
        async targetCompoundToggle({ rootState, dispatch, getters }, targetCompound) {
            return
            const api = rootState.api;
            const targetCompoundId = targetCompound.target_compound_id;
            // get updated selection
            const {
                nextOwnSelection,
                nextChildSelection,
                nextPeerSelection
            } = getters['targetCompoundNextSelection'](targetCompoundId);
            // save toggled isotopes and next selection in temp table
            if (nextPeerSelection == null) {
                await api.query(`--sql
                    CREATE TEMPORARY TABLE toggled_target_compound AS
                        SELECT
                            target_compound_id,
                            ${nextChildSelection} AS next_selection
                        FROM target_compound_filter
                        NATURAL JOIN target_ion
                        WHERE target_compound_id == '${targetCompoundId}'
                `);
            } else {
                await api.query(`--sql
                    CREATE TEMPORARY TABLE toggled_target_compound AS
                        SELECT
                            target_compound_id,
                            CASE
                                WHEN target_compound_id == '${targetCompoundId}' THEN ${nextChildSelection}
                                ELSE ${nextPeerSelection}
                            END AS next_selection
                        FROM target_compound_filter
                        NATURAL JOIN target_ion
                `);
            }
            // create focus clause
            const targetCompoundFocusClause = `--sql
                WHEN target_compound_id == '${targetCompoundId}' THEN ${nextOwnSelection}
            `
            dispatch('updateTargetFilters', { targetCompoundFocusClause });
        },
        async targetIonToggle({ rootState, dispatch, getters }, targetIon) {
            return
            const api = rootState.api;
            const targetIonId = targetIon.target_ion_id;
            // get updated selection
            const {
                nextOwnSelection,
                nextChildSelection,
                nextPeerSelection
            } = getters['targetIonNextSelection'](targetIonId);
            // save toggled isotopes and next selection in temp table
            if (nextPeerSelection == null) {
                await api.query(`--sql
                    CREATE TEMPORARY TABLE toggled_target_ion AS
                        SELECT
                            target_ion_id,
                            ${nextChildSelection} AS next_selection
                        FROM target_ion_filter
                        WHERE target_ion_id == '${targetIonId}'
                `);
            } else {
                await api.query(`--sql
                    CREATE TEMPORARY TABLE toggled_target_ion AS
                        SELECT
                        target_ion_id,
                            CASE
                                WHEN target_ion_id == '${targetIonId}' THEN ${nextChildSelection}
                                ELSE ${nextPeerSelection}
                            END AS next_selection
                        FROM target_ion_filter
                `);
            }
            // create focus clause
            const targetIonFocusClause = `--sql
                WHEN target_ion_id == '${targetIonId}' THEN ${nextOwnSelection}
            `
            dispatch('updateTargetFilters', { targetIonFocusClause });
        },
        async targetIsotopeToggle({ rootState, dispatch, getters }, targetIsotope) {
            return
            const api = rootState.api;
            const targetIsotopeId = targetIsotope.target_isotope_id;
            const {
                nextOwnSelection,
                nextPeerSelection
            } = getters['targetIsotopeNextSelection'](targetIsotopeId);
            // save toggled isotopes and next selection in temp table
            if (nextPeerSelection == null) {
                await api.query(`--sql
                    CREATE TEMPORARY TABLE toggled_target_isotope AS
                        SELECT
                            '${targetIsotopeId}' AS target_isotope_id
                            ${nextOwnSelection} AS next_selection
                `);
            } else {
                await api.query(`--sql
                    CREATE TEMPORARY TABLE toggled_target_isotope AS
                        SELECT
                            target_isotope_id,
                            CASE
                                WHEN target_isotope_id == '${targetIsotopeId}' THEN ${nextOwnSelection}
                                ELSE ${nextPeerSelection}
                            END AS next_selection
                        FROM target_isotope_filter
                `);
            }
            dispatch('updateTargetFilters');
        },
        // internal target consistancy API - do not use externally
        async updateTargetFilters({ rootState, dispatch }, {
            targetIonFocusClause = "",
            targetCompoundFocusClause = "",
            targetCollectionFocusClause = ""
        }) {
            const api = rootState.api;
            // Iterate filter state using temporary tables
            await api.query(`--sql
                DROP TABLE IF EXISTS target_isotope_filter;
                CREATE TEMPORARY TABLE target_isotope_filter AS
                    SELECT
                        target_isotope_id,
                    CASE
                            WHEN target_isotope_id IN toggled THEN toggled.next_selection
                            WHEN target_isotope_id NOT IN toggled THEN current.selection
                        END AS selection
                    FROM target_isotope_filter current
                    NATURAL JOIN toggled_target_isotope toggled;

                DROP TABLE IF EXISTS target_ion_filter;
                CREATE TEMPORARY TABLE target_ion_filter AS
                    SELECT
                        target_ion_id,
                        CASE
                            ${targetIonFocusClause}
                            WHEN 2 <= ALL(List(isotope.selection)) THEN 2
                            WHEN 0 == ALL(List(isotope.selection)) THEN 0
                            ELSE 1
                        END AS selection
                    FROM target_isotope_selection isotope
                    NATURAL JOIN target_ion
                    GROUP BY ALL;

                DROP TABLE IF EXISTS target_compound_filter;
                CREATE TEMPORARY TABLE target_compound_filter AS
                    SELECT
                        target_compound_id,
                        CASE
                            ${targetCompoundFocusClause}
                            WHEN 2 <= ALL(List(ion.selection)) THEN 2
                            WHEN 0 == ALL(List(ion.selection)) THEN 0
                            ELSE 1
                        END AS selection
                    FROM target_ion_filter ion
                    NATURAL JOIN target_compound_in_target_collection
                    GROUP BY ALL;

                DROP TABLE IF EXISTS target_collection_filter;
                CREATE TEMPORARY TABLE target_collection_filter AS
                    SELECT
                        target_collection_id,
                        CASE
                            ${targetCollectionFocusClause}
                            WHEN 2 <= ALL(List(compound.selection)) THEN 2
                            WHEN 0 == ALL(List(compound.selection)) THEN 0
                            ELSE 1
                        END AS selection
                    FROM target_compound_filter compound
                    GROUP BY ALL;
                `);
            dispatch('reload')
        },
    },
    getters: {
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
        // get selection mode
        selectionMode: (state, getters, rootState) => {
            // keyboard shortcuts set operation mode
            let mode;
            if (rootState.key.alt) {
                mode = 'focus';
            } else if (rootState.key.control) {
                mode = 'multiselect'
            } else {
                mode = 'singleselect'
            }
            return mode;
        },
        // get next selection from id
        sampleItemNextSelection: (state, getters) => (sampleItemId) => {
            const mode = getters['selectionMode'];
            const currentSelection =
                getters['sampleItem'](sampleItemId).selection;
            return nextSelection(mode, currentSelection);
        },
        targetCollectionNextSelection: (state, getters) => (targetCollectionId) => {
            const mode = getters['selectionMode'];
            const currentSelection =
                getters['targetCollection'](targetCollectionId).selection;
            return nextSelection(mode, currentSelection);
        },
        targetCompoundNextSelection: (state, getters) => (targetCompoundId) => {
            const mode = getters['selectionMode'];
            const currentSelection =
                getters['targetCompound'](targetCompoundId).selection;
            return nextSelection(mode, currentSelection);
        },
        targetIonNextSelection: (state, getters) => (targetIonId) => {
            const mode = getters['selectionMode'];
            const currentSelection =
                getters['targetIon'](targetIonId).selection;
            return nextSelection(mode, currentSelection);
        },
        targetIsotopeNextSelection: (state, getters) => (targetIsotopeId) => {
            const mode = getters['selectionMode'];
            const currentSelection =
                getters['targetIsotope'](targetIsotopeId).selection;
            return nextSelection(mode, currentSelection);
        },
    }
}

// get next selection based on mode and current selection
function nextSelection(mode, currentSelection) {
    const mapSelection = {
        0: 2,  // unselected => selected
        1: 2,  // semiselected => selected
        2: 0,  // selected => unselected
        3: 0   // focused => unselected
    };
    const mapFocus = {
        0: 3,  // unselected => focused
        1: 3,  // semiselected => focused
        2: 3,  // selected => focused
        3: 2   // focused => selected
    };
    let nextOwnSelection, nextPeerSelection;
    switch (mode) {
        case 'singleselect': {
            nextOwnSelection = mapSelection[currentSelection];
            nextPeerSelection = 0;  // deselect peers
            break;
        }
        case 'multiselect': {
            nextOwnSelection = mapSelection[currentSelection];
            nextPeerSelection = null;  // do not change peers
            break;
        }
        case 'focus': {
            nextOwnSelection = mapFocus[currentSelection];
            nextPeerSelection = null;  // do not change peers
            break;
        }
    }
    const nextChildSelection = currentSelection < 2 ? 2 : 0;
    return { nextOwnSelection, nextChildSelection, nextPeerSelection }
}

async function allFiltersExist(api) {
    const tables = (await api.query(`--sql
            describe;
        `))
        .getChild('table_name')
        .toArray();
    const filterTables = [
        'sample_item_filter',
        'target_isotope_filter',
        'target_ion_filter',
        'target_compound_filter',
        'target_collection_filter'
    ];
    return filterTables
        .every((filterTable) => tables.includes(filterTable));
}