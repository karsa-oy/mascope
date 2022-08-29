import { make } from 'vuex-pathify';

const state = {
    active: null,
    // samples
    sampleItems: null,
    // targets
    targetCollections: null,
    targetCompounds: null,
    targetIons: null,
    targetIsotopes: null,
    // matches
    matchCompounds: null,
    matchIons: null,
}

export default {
    namespaced: true,
    state,
    mutations: make.mutations(state),
    actions: {
        async load({ rootState, commit, dispatch }, batch) {
            const api = rootState.api;
            const batchId = batch.sample_batch_id;
            await commit('SET_ACTIVE', null);
            await dispatch('initFilters', batchId);
            // load data w/ statistical aggregates
            const stats = `--sql
                max(selected(match_score, selection))
                    AS match_score,
                sum(selected(sample_peak_height, selection))
                    AS sample_peak_height_sum
            `;
            // load sample items
            await api.query(`--sql
                SELECT
                    sample_item.*,
                    sample_file_id,
                    datetime,
                    datetime_utc,
                    length,
                    range,
                    mz_calibration,
                    selection
                FROM sample_item_filter
                NATURAL LEFT JOIN sample_item
                NATURAL LEFT JOIN sample_file
            `).then((res) => {
                commit('SET_SAMPLE_ITEMS', res);
            });
            // load target isotopes
            await api.query(`--sql
                SELECT
                    target_isotope.*,
                    selection
                FROM target_isotope_filter
                NATURAL LEFT JOIN target_isotope
            `).then((res) => {
                commit('SET_TARGET_ISOTOPES', res);
            });
            // load target ions
            await api.query(`--sql
                SELECT
                    target_ion.*,
                    config_mechanism.*,
                    selection
                FROM target_ion_filter
                NATURAL LEFT JOIN target_ion
                NATURAL LEFT JOIN config_mechanism
            `).then((res) => {
                commit('SET_TARGET_IONS', res);
            });
            // load target compounds
            await api.query(`--sql
                SELECT
                    target_compound.*,
                    target_collection_id,
                    selection
                FROM target_compound_filter
                NATURAL LEFT JOIN target_compound
                NATURAL LEFT JOIN target_compound_in_target_collection
            `).then((res) => {
                commit('SET_TARGET_COMPOUNDS', res);
            });
            // load target collections
            await api.query(`--sql
                SELECT
                    target_collection.*,
                    selection
                FROM target_collection_filter
                NATURAL LEFT JOIN target_collection
            `).then((res) => {
                commit('SET_TARGET_COLLECTIONS', res);
            });
            // load matches
            await api.query(`--sql
                SELECT
                    sample_item_id,
                    target_compound_id,
                    AVG(match_score) AS match_score,
                    SUM(sample_peak_height) AS sample_peak_height_sum
                FROM match_filter
                GROUP BY sample_item_id, target_compound_id, target_ion_id;
            `).then((res) => {
                commit('SET_MATCH_IONS', res);
            });
            await api.query(`--sql
                SELECT
                    sample_item_id,
                    target_compound_id,
                    AVG(match_score) AS match_score,
                    SUM(sample_peak_height) AS sample_peak_height_sum
                FROM match_filter
                GROUP BY sample_item_id, target_compound_id;
            `).then((res) => {
                commit('SET_MATCH_COMPOUNDS', res);
            });
            // set batch active
            await commit('SET_ACTIVE', batch);
        },
        async unload({ commit }) {
            commit('SET_ACTIVE', null);
            // samples
            commit('SET_SAMPLE_ITEMS', null);
            // targets
            commit('SET_TARGET_COLLECTIONS', null);
            commit('SET_TARGET_COMPOUNDS', null);
            commit('SET_TARGET_IONS', null);
            commit('SET_TARGET_ISOTOPES', null);
            // matches
            commit('SET_MATCH_COMPOUNDS', null);
            commit('SET_MATCH_IONS', null);
        },
        async reload({ dispatch, state }) {
            if (state.active) {
                dispatch('load', state.active);
            }
        },
        async onBatchReload({ state, dispatch }, batch) {
            if (state.active.sample_batch_id == batch.sample_batch_id) {
                dispatch('reload');
            }
        },
        async batchToggle({ state, dispatch }, batch) {
            const active_batch_id = state.active
                ? state.active.sample_batch_id
                : null;
            if (active_batch_id == batch.sample_batch_id) {
                dispatch('unload');
            } else {
                dispatch('load', batch);
            }
        },
        // selection
        async initFilters({ rootState }, batchId) {
            const api = rootState.api;
            await api.query(`--sql
                DROP TABLE IF EXISTS sample_item_filter;
            `);
            await api.query(`--sql
                -- samples
                CREATE TEMPORARY TABLE sample_item_filter AS
                    SELECT
                        sample_item_id
                        ,2 as selection
                    FROM sample_item
                    WHERE sample_batch_id == '${batchId}'
            `);
            await api.query(`--sql
                DROP TABLE IF EXISTS target_collection_filter;
            `);
            await api.query(`--sql
                CREATE TEMPORARY TABLE target_collection_filter AS
                    SELECT
                        target_collection_id
                        ,2 as selection
                    FROM target_collection
                    NATURAL JOIN target_collection_in_sample_batch
                    WHERE sample_batch_id == '${batchId}'
            `);
            await api.query(`--sql
                DROP TABLE IF EXISTS target_compound_filter;
            `);
            await api.query(`--sql
                CREATE TEMPORARY TABLE target_compound_filter AS
                    SELECT
                        target_compound_id
                        ,2 as selection
                    FROM target_compound
                    NATURAL JOIN target_compound_in_target_collection
                    NATURAL JOIN target_collection_in_sample_batch
                    WHERE sample_batch_id == '${batchId}'
            `);
            await api.query(`--sql
                DROP TABLE IF EXISTS target_ion_filter;
            `);
            await api.query(`--sql
                CREATE TEMPORARY TABLE target_ion_filter AS
                    SELECT
                        target_ion_id
                        ,2 as selection
                    FROM target_ion
                    NATURAL JOIN target_compound_in_target_collection
                    NATURAL JOIN target_collection_in_sample_batch
                    WHERE sample_batch_id == '${batchId}'
            `);
            await api.query(`--sql
                DROP TABLE IF EXISTS target_isotope_filter;
            `);
            await api.query(`--sql
                -- targets
                CREATE TEMPORARY TABLE target_isotope_filter AS
                    SELECT
                        target_isotope_id
                        ,2 as selection
                    FROM target_isotope
                    NATURAL JOIN target_ion
                    NATURAL JOIN target_compound_in_target_collection
                    NATURAL JOIN target_collection_in_sample_batch
                    WHERE sample_batch_id == '${batchId}'
            `);
            await api.query(`--sql
                DROP TABLE IF EXISTS match_filter;
            `);
            await api.query(`--sql
                -- matches
                CREATE TEMPORARY TABLE match_filter AS
                    SELECT
                        match.*,
                        target_ion_id,
                        target_compound_id
                        ,2 as selection
                    FROM sample_item
                    NATURAL LEFT JOIN match
                    NATURAL LEFT JOIN target_isotope
                    NATURAL LEFT JOIN target_ion
                    WHERE sample_batch_id == '${batchId}'
            `);
        },
        // Sample selection toggling
        // Directly updates the sample filter
        async sampleItemToggle({ rootState, dispatch, getters, state }, sampleItemToggled) {
            const api = rootState.api;
            const sampleItemToggledId = sampleItemToggled.sample_item_id;
            // get updated selection
            const {
                nextOwnSelection,
                nextPeerSelection
            } = getters['sampleItemNextSelection'](sampleItemToggledId);
            if (nextOwnSelection == 3) {
                // Clear previous focus if any
                state.sampleItems.filter(
                    (item) => (item.selection == 3)
                    ).forEach((prevFocusedItem) => { prevFocusedItem.selection = 2 });
            }
            getters['sampleItem'](sampleItemToggledId).selection = nextOwnSelection;
            // // update sample item filter directly
            // if (nextPeerSelection == null) {
            //     await api.query(`--sql
            //         CREATE TEMPORARY TABLE sample_item_filter AS
            //             SELECT
            //                 sample_item_id,
            //                 CASE
            //                     WHEN (
            //                         sample_item_id == '${sampleItemId}'
            //                     ) THEN ${nextOwnSelection}
            //                     ELSE current.selection
            //                 END AS next_selection
            //             FROM sample_item_filter current
            //     `);
            // } else {
            //     await api.query(`--sql
            //         CREATE TEMPORARY TABLE sample_item_filter AS
            //             SELECT
            //                 sample_item_id,
            //                 CASE
            //                     WHEN (
            //                         sample_item_id == '${sampleItemId}'
            //                     ) THEN ${nextOwnSelection}
            //                     ELSE ${nextPeerSelection}
            //                 END AS next_selection
            //             FROM sample_item_filter
            //     `);
            // }
            // dispatch('reload');
        },
        // Target selection toggling actions
        // these retrieve toggled isotope selections and trigger the updateTargetFilter 
        // action which propagates these to up the hierarchy.
        async targetCollectionToggle({ rootState, dispatch, getters }, targetCollection) {
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
                CREATE TEMPORARY TABLE target_isotope_filter AS
                    SELECT
                        target_isotope_id,
                    CASE
                            WHEN target_isotope_id IN toggled THEN toggled.next_selection
                            WHEN target_isotope_id NOT IN toggled THEN current.selection
                        END AS selection
                    FROM target_isotope_filter current
                    NATURAL JOIN toggled_target_isotope toggled
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
                    GROUP BY ALL
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
                    GROUP BY ALL
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
                    GROUP BY ALL
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
        sampleItemsToCalibrate: (state, getters) => {
            return getters['sampleItems']
                .filter((sampleItem) => sampleItem.selection == 2);
        },
        sampleItemFocused: (state, getters) => {
            return getters['sampleItems']
                .filter((sampleItem) => sampleItem.selection == 3);
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