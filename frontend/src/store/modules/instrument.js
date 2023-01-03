import { dispatch, make } from 'vuex-pathify';

const state = {
    active: null,
    calibrationProgress: 0,
    acquisitionActiveFilename: null,
    acquisitionProgress: 0,
    acquisitions: null,
    conversionProgress: 0,
    matchingProgress: 0,
    mzCalibration: null,
    recentAcquisitions: null,
    scenthoundModeActive: false,
}

export default {
    namespaced: true,
    state,
    mutations: make.mutations(state),
    actions: {
        async getAcquisitions({ state, rootState, commit }, datetimeRange) {
            const minDatetime = datetimeRange.min.toISOString();
            const maxDatetime = datetimeRange.max.toISOString();
            await rootState.api.query(`--sql
                SELECT
                    sample_file_id,
                    filename,
                    instrument,
                    datetime,
                    datetime_utc,
                    length,
                    range,
                    mz_calibration
                FROM sample_file
                WHERE (
                    (
                        JulianDay(datetime_utc) >= JulianDay('${minDatetime}') AND
                        JulianDay(datetime_utc) <= JulianDay('${maxDatetime}')
                    )
                AND
                    instrument IN (
                    '${state.active}'
                    )
                )
                ORDER BY datetime_utc ASC;
            `).then((res) => { commit('SET_ACQUISITIONS', res) });
        },
        async getRecentAcquisitions({ state, rootState, commit }) {
            await rootState.api.query(`--sql
                SELECT
                    sample_file_id,
                    filename,
                    instrument,
                    datetime,
                    datetime_utc,
                    length,
                    range,
                    mz_calibration
                FROM sample_file
                WHERE (
                    (JulianDay('now') - JulianDay(datetime_utc) ) <= 1
                AND
                    instrument IN (
                    '${state.active}'
                    )
                )
                ORDER BY datetime_utc ASC;
            `).then((res) => { commit('SET_RECENT_ACQUISITIONS', res) });
        },
        async getMzCalibration({ rootState, state, commit }) {
            await rootState.api.query(`--sql
                SELECT mz_calibration
                FROM sample_file
                WHERE (
                    datetime_utc = (
                        SELECT MAX(datetime_utc)
                        FROM sample_file
                        WHERE (
                            instrument == '${state.active}'
                        AND
                            mz_calibration NOT NULL
                        )
                    )
                );
            `).then((res) => {
                const mz_calibration = res.length ? res[0].mz_calibration : null;
                commit('SET_MZ_CALIBRATION', mz_calibration)
                });
        },
        async load({ rootState, commit, dispatch }, instrument) {
            if (state.active) await dispatch('unload');
            rootState.api.emit('subscribe', instrument);
            await commit('SET_ACTIVE', instrument);
            await dispatch('getMzCalibration');
            await dispatch('getRecentAcquisitions');
        },
        async matchSample({ rootState, dispatch }) {
            const sampleActive = rootState.sample.active;
            if (sampleActive) {
                rootState.api.emit(
                    'match_item_compute',
                    {
                        'filename': sampleActive.filename,
                        'sample_item_id': sampleActive.sample_item_id,
                        'sample_batch_id': sampleActive.sample_batch_id,
                    }
                );
            } else {
                // Try again in 1 second
                setTimeout(() => {
                    dispatch('matchSample')
                }, 1000);
            }
        },
        async mzCalibrateSample({ rootState, dispatch }) {
            const sampleActive = rootState.sample.active;
            if (sampleActive) {
                rootState.api.emit(
                    'calibration_mz_calibrate_sample',
                    {
                        'filename': sampleActive.filename,
                        'sample_item_id': sampleActive.sample_item_id,
                        'sample_batch_id': sampleActive.sample_batch_id,
                    }
                );
            } else {
                // Try again in 1 second
                setTimeout(() => {
                    dispatch('mzCalibrateSample')
                }, 1000);
            }
        },
        async resetProgress({ commit }) {
            commit('SET_ACQUISITION_ACTIVE_FILENAME', null);
            commit('SET_ACQUISITION_PROGRESS', 0);
            commit('SET_CALIBRATION_PROGRESS', 0);
            commit('SET_CONVERSION_PROGRESS', 0);
            commit('SET_MATCHING_PROGRESS', 0);
        },
        async unload({ rootState, state, commit, dispatch }) {
            if (!state.active) return;
            rootState.api.emit('unsubscribe', state.active);
            commit('SET_ACTIVE', null);
            commit('SET_MZ_CALIBRATION', null);
            commit('SET_ACQUISITIONS', null);
            commit('SET_RECENT_ACQUISITIONS', null);
            await dispatch('resetProgress');
            commit('SET_SCENTHOUND_MODE_ACTIVE', false);
        },
        // notifications
        async onInstrumentAcquisitionFinished({ commit }, data) {
            commit('SET_ACQUISITION_ACTIVE_FILENAME', data.filename);
            commit('SET_ACQUISITION_PROGRESS', data.progress);
        },
        async onInstrumentAcquisitionProgress({ commit }, data) {
            commit('SET_ACQUISITION_ACTIVE_FILENAME', data.filename);
            commit('SET_ACQUISITION_PROGRESS', data.progress);
        },
        async onInstrumentAcquisitionStarted({ rootState, commit, dispatch }, data) {
            await dispatch('sample/unload', null, {root:true});
            await dispatch('resetProgress');
            commit('SET_ACQUISITION_ACTIVE_FILENAME', data.filename);
            commit('SET_ACQUISITION_PROGRESS', data.progress);
        },
        async onCalibrationMzCalibrateFailed({ commit }, data) {
            commit('SET_CALIBRATION_PROGRESS', data.progress);
            // TODO:
        },
        async onCalibrationMzCalibrateFinished({ state, commit }, data) {
            commit('SET_CALIBRATION_PROGRESS', data.progress);
            // Start matching
            if (state.scenthoundModeActive) {
                dispatch('instrument/matchSample', null, {root:true});
            }
        },
        async onCalibrationMzCalibrateProgress({ commit }, data) {
            commit('SET_CALIBRATION_PROGRESS', data.progress);
        },
        async onCalibrationMzCalibrateStarted({ commit }, data) {
            commit('SET_CALIBRATION_PROGRESS', data.progress);
        },
        async onInstrumentConversionFinished({ state, commit, dispatch }, data) {
            commit('SET_CONVERSION_PROGRESS', data.progress);
            // Wait for sample to be saved, then start mass calibration
            if (state.scenthoundModeActive) {
                dispatch('mzCalibrateSample');
            }
        },
        async onInstrumentConversionProgress({ commit }, data) {
            commit('SET_CONVERSION_PROGRESS', data.progress);
        },
        async onInstrumentConversionStarted({ commit }, data) {
            commit('SET_CONVERSION_PROGRESS', data.progress);
        },
        async onMatchItemComputeFailed({ commit }, data) {
            commit('SET_MATCHING_PROGRESS', data.progress);
        },
        async onMatchItemComputeFinished({ commit }, data) {
            commit('SET_MATCHING_PROGRESS', data.progress);
            // TODO: case: background, verify interferences
            // TODO: case: else, display matches
        },
        async onMatchItemComputeProgress({ commit }, data) {
            commit('SET_MATCHING_PROGRESS', data.progress);
        },
        async onMatchItemComputeStarted({ commit }, data) {
            commit('SET_MATCHING_PROGRESS', data.progress);
        },
        async onSampleFileCreated({ rootState, dispatch }, filename) {
            await dispatch('api/reloadDb', null, {root:true});
            await dispatch('getRecentAcquisitions');
        },
    },
    getters: {}
}