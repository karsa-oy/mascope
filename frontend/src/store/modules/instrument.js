import { make } from 'vuex-pathify';

const state = {
    active: null,
    calibrationProgress: 0,
    acquisitionProgress: 0,
    acquisitions: null,
    conversionProgress: 0,
    matchingProgress: 0,
    mzCalibration: null,
    recentAcquisitions: null,
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
        async resetProgress({ commit }) {
            commit('SET_ACQUISITION_PROGRESS', 0);
            commit('SET_CALIBRATION_PROGRESS', 0);
            commit('SET_CONVERSION_PROGRESS', 0);
            commit('SET_MATCHING_PROGRESS', 0);
        },
        async unload({ rootState, state, commit }) {
            if (!state.active) return;
            rootState.api.emit('unsubscribe', state.active);
            commit('SET_ACTIVE', null);
            commit('SET_MZ_CALIBRATION', null);
            commit('SET_ACQUISITIONS', null)
            commit('SET_RECENT_ACQUISITIONS', null)
        },
        // notifications
        async onInstrumentAcquisitionFinished({ commit }, data) {
            commit('SET_ACQUISITION_PROGRESS', data.progress);
        },
        async onInstrumentAcquisitionProgress({ commit }, data) {
            commit('SET_ACQUISITION_PROGRESS', data.progress);
        },
        async onInstrumentAcquisitionStarted({ rootState, commit, dispatch }, data) {
            await dispatch('sample/unload', null, {root:true});
            await dispatch('resetProgress');
            commit('modal/activate', {modal: 'scenthoundWorkflow'}, {root:true});
            rootState.modal.scenthoundWorkflowProps = {
                action: 'create',
                sampleItemRecordToLoad: data,
            };
            commit('SET_ACQUISITION_PROGRESS', data.progress);
        },
        async onInstrumentCalibrationFinished({ commit }, data) {
            commit('SET_CALIBRATION_PROGRESS', data.progress);
        },
        async onInstrumentCalibrationProgress({ commit }, data) {
            commit('SET_CALIBRATION_PROGRESS', data.progress);
        },
        async onInstrumentCalibrationStarted({ commit }, data) {
            commit('SET_CALIBRATION_PROGRESS', data.progress);
        },
        async onInstrumentConversionFinished({ rootState, commit }, data) {
            commit('SET_CONVERSION_PROGRESS', data.progress);
            // TODO: TOFService: acquisition_started -> Prompt input from user
            const sampleActive = rootState.sample.active;
            if (sampleActive && rootState.modal.scenthoundWorkflowActive) {
                rootState.api.emit(
                    'scenthound_process_sample',
                    {
                        'filename': sampleActive.filename,
                        'sample_item_id': sampleActive.sample_item_id,
                        'sample_batch_id': sampleActive.sample_batch_id,
                    }
                ); 
            }
            // TODO
        },
        async onInstrumentConversionProgress({ commit }, data) {
            commit('SET_CONVERSION_PROGRESS', data.progress);
        },
        async onInstrumentConversionStarted({ commit }, data) {
            commit('SET_CONVERSION_PROGRESS', data.progress);
        },
        async onInstrumentMatchingFinished({ commit }, data) {
            commit('SET_MATCHING_PROGRESS', data.progress);
        },
        async onInstrumentMatchingProgress({ commit }, data) {
            commit('SET_MATCHING_PROGRESS', data.progress);
        },
        async onInstrumentMatchingStarted({ commit }, data) {
            commit('SET_MATCHING_PROGRESS', data.progress);
        },
        async onSampleFileCreated({ rootState, dispatch }, filename) {
            await dispatch('api/reloadDb', null, {root:true});
            await dispatch('getRecentAcquisitions');
        },
    },
    getters: {}
}