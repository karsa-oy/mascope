import { make } from 'vuex-pathify';

const state = {
    active: null,
    // samples
    sampleItems: [],
    // targets
    targetCollections: [],
    targetCompounds: [],
    targetIons: [],
    targetIsotopes: [],
}

export default {
    namespaced: true,
    state,
    mutations: make.mutations(state),
    actions: {
        async load({ rootState, state, commit }, batchId) {
            const api = rootState.api;
            await commit('SET_ACTIVE', null);
            // load data w/ statistical aggregates
            const stats = `--sql
                max(coalesce(match_score, 0)) AS match_score,
                sum(coalesce(sample_peak_height,0)) AS sample_peak_height
            `
            await Promise.all([
                // load sample items
                api.query(`--sql
                    WITH sample_item_in_batch AS (
                        SELECT
                            *
                        FROM sample_item
                        WHERE sample_batch_id == '${batchId}'
                    )
                    SELECT
                        sample_item_in_batch.*
                        sample_file.*,
                        ${stats}
                    FROM sample_item_in_batch
                    NATURAL LEFT JOIN sample_file
                    NATURAL LEFT JOIN match
                    GROUP BY ALL
                `).then((res) => {
                    commit('SET_SAMPLE_ITEMS', res.toArray());
                }),
                // load target isotopes
                api.query(`--sql
                    WITH target_isotope_in_batch AS (
                        SELECT
                            *
                        FROM target_isotope
                        NATURAL JOIN target_ion
                        NATURAL JOIN target_compound_in_target_collection
                        NATURAL JOIN target_collection_in_sample_batch
                        WHERE sample_batch_id == '${batchId}';
                    )
                    SELECT
                        target_isotope_in_batch.*,
                        match.sample_peak_height,
                        match.match_score
                    FROM target_isotope_in_batch
                    NATURAL LEFT JOIN match
                `).then((res) => {
                    commit('SET_TARGET_ISOTOPES', res.toArray());
                }),
                // load target ions
                api.query(`--sql
                    WITH target_ion_in_batch AS (
                        SELECT
                            *
                        FROM target_ion
                        NATURAL JOIN target_compound_in_target_collection
                        NATURAL JOIN target_collection_in_sample_batch
                        WHERE sample_batch_id == '${batchId}'
                    )
                    SELECT
                        target_ion_in_batch.*,
                        config_mechanism.*,
                        ${stats}
                    FROM target_ion_in_batch
                    NATURAL LEFT JOIN config_mechanism
                    NATURAL LEFT JOIN target_isotope
                    NATURAL LEFT JOIN match
                    GROUP BY ALL;
                `).then((res) => {
                    commit('SET_TARGET_IONS', res.toArray());
                }),
                // load target compounds
                api.query(`--sql
                    WITH target_compound_in_batch AS (
                        SELECT
                            *
                        FROM target_compound
                        NATURAL JOIN target_compound_in_target_collection
                        NATURAL JOIN target_collection_in_sample_batch
                        WHERE sample_batch_id == '${batchId}'
                    )
                    SELECT
                        target_compound_in_batch.*,
                        ${stats}
                    FROM target_compound_in_batch
                    NATURAL LEFT JOIN target_ion
                    NATURAL LEFT JOIN target_isotope
                    NATURAL LEFT JOIN match
                    GROUP BY ALL;
                `).then((res) => {
                    commit('SET_TARGET_COMPOUNDS', res.toArray())
                }),
                // load target collections
                api.query(`--sql
                    WITH target_collection_in_batch (
                        SELECT
                            *
                        FROM target_collection
                        NATURAL JOIN target_collection_in_sample_batch
                        WHERE sample_batch_id == '${batchId}'
                    )
                    SELECT
                        target_collection_in_batch.*,
                        ${stats}
                    FROM target_collection_in_batch
                    NATURAL LEFT JOIN target_compound_in_target_collection
                    NATURAL LEFT JOIN target_ion
                    NATURAL LEFT JOIN target_isotope
                    NATURAL LEFT JOIN match
                    GROUP BY ALL;
                `).then((res) => {
                    commit('SET_TARGET_COLLECTIONS', res.toArray())
                }),
            ]);
            await commit('SET_ACTIVE', batchId);
        },
        async unload({ commit }) {
            commit('SET_ACTIVE', null);
            // samples
            commit('SET_SAMPLE_ITEMS', []);
            // targets
            commit('SET_TARGET_COLLECTIONS', []);
            commit('SET_TARGET_COMPOUNDS', []);
            commit('SET_TARGET_IONS', []);
            commit('SET_TARGET_ISOTOPES', []);
        },
        async reload({ dispatch, state }) {
            if (state.active) {
                dispatch('load', state.active);
            }
        },
        async onBatchReload({ state, dispatch }, batchId) {
            if (state.active == batchId) {
                dispatch('reload');
            }
        },
        // Sample selection toggling
        // Directly updates the sample filter
        toggleSampleItem({ dispatch, getters }, { sampleItemId }) {
            // get updated selection
            const {
                nextOwnSelection,
                nextPeerSelection
            } = getters['sampleItemNextSelection'](sampleItemId);
            // update sample item filter directly
            if (nextPeerSelection == null) {
                await api.query(`--sql
                    CREATE OR REPLACE TEMPORARY TABLE sample_item_filter AS (
                        SELECT
                            sample_item_id,
                            CASE
                                WHEN (
                                    sample_item_id == '${sampleItemId}'
                                ) THEN ${nextOwnSelection}
                                ELSE current.selection
                            END AS next_selection
                        FROM sample_item_filter current
                    );
                `);
            } else {
                await api.query(`--sql
                    CREATE OR REPLACE TEMPORARY TABLE sample_item_filter AS (
                        SELECT
                            sample_item_id,
                            CASE
                                WHEN (
                                    sample_item_id == '${sampleItemId}'
                                ) THEN ${nextOwnSelection}
                                ELSE ${nextPeerSelection}
                            END AS next_selection
                        FROM sample_item_filter
                    );
                `);
            }
            dispatch('reload');
        },
        // Target selection toggling actions
        // these retrieve toggled isotope selections and trigger the updateTargetFilter 
        // action which propagates these to up the hierarchy.
        targetCollectionToggle({ dispatch, getters }, { targetCollectionId }) {
            // get updated selection
            const {
                nextOwnSelection,
                nextChildSelection,
                nextPeerSelection
            } = getters['targetCollectionNextSelection'](targetCollectionId);
            // save toggled isotopes and next selection in temp table
            if (nextPeerSelection == null) {
                await api.query(`--sql
                    CREATE OR REPLACE TEMPORARY TABLE toggled_isotope AS (
                        SELECT
                            target_isotope_id,
                            ${nextChildSelection} AS next_selection
                        FROM target_isotope_filter
                        NATURAL JOIN target_ion
                        NATURAL JOIN target_compound_in_target_collection
                        WHERE target_collection_id == '${targetCollectionId}'
                    );
                `);
            } else {
                await api.query(`--sql
                    CREATE OR REPLACE TEMPORARY TABLE toggled_isotope AS (
                        SELECT
                            target_isotope_id,
                            CASE
                                WHEN target_collection_id == '${targetCollectionId}' THEN ${nextChildSelection}
                                ELSE ${nextPeerSelection}
                            END AS next_selection
                        FROM target_isotope_filter
                        NATURAL JOIN target_ion
                        NATURAL JOIN target_compound_in_target_collection
                    );
                `);
            }
            // create focus clause
            const targetCollectionFocusClause = `--sql
                WHEN target_collection_id == '${targetCollectionId}' THEN ${nextOwnSelection}
            `
            dispatch('updateTargetFilters', { targetCollectionFocusClause });
        },
        targetCompoundToggle({ dispatch, getters }, { targetCompoundId }) {
            // get updated selection
            const {
                nextOwnSelection,
                nextChildSelection,
                nextPeerSelection
            } = getters['targetCompoundNextSelection'](targetCompoundId);
            // save toggled isotopes and next selection in temp table
            if (nextPeerSelection == null) {
                await api.query(`--sql
                    CREATE OR REPLACE TEMPORARY TABLE toggled_isotope AS (
                        SELECT
                            target_isotope_id,
                            ${nextChildSelection} AS next_selection
                        FROM target_isotope_filter
                        NATURAL JOIN target_ion
                        WHERE target_compound_id == '${targetCompoundId}'
                    );
                `);
            } else {
                await api.query(`--sql
                    CREATE OR REPLACE TEMPORARY TABLE toggled_isotope AS (
                        SELECT
                            target_isotope_id,
                            CASE
                                WHEN target_compound_id == '${targetCompoundId}' THEN ${nextChildSelection}
                                ELSE ${nextPeerSelection}
                            END AS next_selection
                        FROM target_isotope_filter
                        NATURAL JOIN target_ion
                    );
                `);
            }
            // create focus clause
            const targetCompoundFocusClause = `--sql
                WHEN target_compound_id == '${targetCompoundId}' THEN ${nextOwnSelection}
            `
            dispatch('updateTargetFilters', { targetCompoundFocusClause });
        },
        targetIonToggle({ dispatch, getters }, { targetIonId }) {
            // get updated selection
            const {
                nextOwnSelection,
                nextChildSelection,
                nextPeerSelection
            } = getters['targetIonNextSelection'](targetIonId);
            // save toggled isotopes and next selection in temp table
            if (nextPeerSelection == null) {
                await api.query(`--sql
                    CREATE OR REPLACE TEMPORARY TABLE toggled_isotope AS (
                        SELECT
                            target_isotope_id,
                            ${nextChildSelection} AS next_selection
                        FROM target_isotope_filter
                        WHERE target_ion_id == '${targetIonId}'
                    );
                `);
            } else {
                await api.query(`--sql
                    CREATE OR REPLACE TEMPORARY TABLE toggled_isotope AS (
                        SELECT
                            target_isotope_id,
                            CASE
                                WHEN target_ion_id == '${targetIonId}' THEN ${nextChildSelection}
                                ELSE ${nextPeerSelection}
                            END AS next_selection
                        FROM target_isotope_filter
                    );
                `);
            }
            // create focus clause
            const targetIonFocusClause = `--sql
                WHEN target_ion_id == '${targetIonId}' THEN ${nextOwnSelection}
            `
            dispatch('updateTargetFilters', { targetIonFocusClause });
        },
        targetIsotopeToggle({ dispatch, getters }, { targetIsotopeId }) {
            const {
                nextOwnSelection,
                nextPeerSelection
            } = getters['targetIsotopeNextSelection'](targetIsotopeId);
            // save toggled isotopes and next selection in temp table
            if (nextPeerSelection == null) {
                await api.query(`--sql
                    CREATE OR REPLACE TEMPORARY TABLE toggled_isotope AS (
                        SELECT
                            '${targetIsotopeId}' AS target_isotope_id
                            ${nextOwnSelection} AS next_selection
                    );
                `);
            } else {
                await api.query(`--sql
                    CREATE OR REPLACE TEMPORARY TABLE toggled_isotope AS (
                        SELECT
                            target_isotope_id,
                            CASE
                                WHEN target_isotope_id == '${targetIsotopeId}' THEN ${nextOwnSelection}
                                ELSE ${nextPeerSelection}
                            END AS next_selection
                        FROM target_isotope_filter
                    );
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
                CREATE OR REPLACE TEMPORARY TABLE target_isotope_filter AS(
                    SELECT
                        target_isotope_id,
                    CASE
                            WHEN target_isotope_id IN toggled THEN toggled.next_selection
                            WHEN target_isotope_id NOT IN toggled THEN current.selection
                        END AS selection
                    FROM target_isotope_filter current
                    NATURAL JOIN toggled_target_isotope toggled
                );
                CREATE OR REPLACE TEMPORARY TABLE target_ion_filter AS(
                    SELECT
                        target_ion_id,
                    target_compound_id,
                    CASE
                            ${targetIonFocusClause}
                            WHEN 2 <= ALL(List(isotope.selection)) THEN 2
                            WHEN 0 == ALL(List(isotope.selection)) THEN 0
                            ELSE 1
                        END AS selection
                    FROM target_isotope_selection isotope
                    NATURAL JOIN target_ion
                    GROUP BY ALL
                );
                CREATE OR REPLACE TEMPORARY TABLE target_compound_filter AS(
                    target_compound_id,
                    target_collection_id,
                    CASE
                            ${targetCompoundFocusClause}
                            WHEN 2 <= ALL(List(ion.selection)) THEN 2
                            WHEN 0 == ALL(List(ion.selection)) THEN 0
                            ELSE 1
                        END AS selection
                    FROM target_ion_filter ion
                    NATURAL JOIN target_compound_in_target_collection
                    GROUP BY ALL
                );
                CREATE OR REPLACE TEMPORARY TABLE target_collection_filter AS(
                    target_collection_id,
                    CASE
                            ${targetCollectionFocusClause}
                            WHEN 2 <= ALL(List(compound.selection)) THEN 2
                            WHEN 0 == ALL(List(compound.selection)) THEN 0
                            ELSE 1
                        END AS selection
                    FROM target_compound_filter compound
                    GROUP BY ALL
                );
                `);
            dispatch('reload')
        },
    },
    getters: {
        // get row from id
        sampleItem: (state) => (sampleItemId) => {
            return state.sampleItems
                .filter((row) => (row.sample_item_id == sampleItemId))[0]
        },
        targetCollection: (state) => (targetCollectionId) => {
            return state.targetCollections
                .filter((row) => (row.sample_item_id == targetCollectionId))[0]
        },
        targetCompound: (state) => (targetCompoundId) => {
            return state.targetCompounds
                .filter((row) => (row.sample_item_id == targetCompoundId))[0]
        },
        targetIon: (state) => (targetIonId) => {
            return state.targetIons
                .filter((row) => (row.sample_item_id == targetIonId))[0]
        },
        targetIsotope: (state) => (targetIsotopeId) => {
            return state.targetIsotopes
                .filter((row) => (row.sample_item_id == targetIsotopeId))[0]
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
        sampleItemNextSelection: (state) => (sampleItemId) => {
            const mode = getters['selectionMode'];
            const currentSelection =
                getters['sampleItem'](sampleItemId).selection;
            return nextSelection(mode, currentSelection);
        },
        targetCollectionNextSelection: (state) => (targetCollectionId) => {
            const mode = getters['selectionMode'];
            const currentSelection =
                getters['targetCollection'](targetCollectionId).selection;
            return nextSelection(mode, currentSelection);
        },
        targetCompoundNextSelection: (state) => (targetCompoundId) => {
            const mode = getters['selectionMode'];
            const currentSelection =
                getters['targetCompound'](targetCompoundId).selection;
            return nextSelection(mode, currentSelection);
        },
        targetIonNextSelection: (state) => (targetIonId) => {
            const mode = getters['selectionMode'];
            const currentSelection =
                getters['targetIon'](targetIonId).selection;
            return nextSelection(mode, currentSelection);
        },
        targetIsotopeNextSelection: (state) => (targetIsotopeId) => {
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
        3: 0   // focused => unselected
    };
    let nextOwnSelection, nextPeerSelection;
    switch (mode) {
        case 'singleselect': {
            nextOwnSelection = mapSelection(currentSelection);
            nextPeerSelection = 0;  // deselect peers
            break;
        }
        case 'multiselect': {
            nextOwnSelection = mapSelection(currentSelection);
            nextPeerSelection = null;  // do not change peers
            break;
        }
        case 'focus': {
            nextOwnSelection = mapFocus(currentSelection);
            nextPeerSelection = null;  // do not change peers
            break;
        }
    }
    const nextChildSelection = currentSelection < 2 ? 2 : 0;
    return { nextOwnSelection, nextChildSelection, nextPeerSelection }
}
