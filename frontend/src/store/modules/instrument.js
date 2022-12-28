import { make } from 'vuex-pathify';

const state = {
    active: null,
    mzCalibration: null,
    acquisitions: null,
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
        async unload({ rootState, state, commit }) {
            if (!state.active) return;
            rootState.api.emit('unsubscribe', state.active);
            commit('SET_ACTIVE', null);
            commit('SET_MZ_CALIBRATION', null);
            commit('SET_ACQUISITIONS', null)
            commit('SET_RECENT_ACQUISITIONS', null)
        },
        // notifications
        async onInstrumentAcquisitionFinished({}, data) {
            console.log(data);
        },
        async onInstrumentAcquisitionProgress({}, data) {
            console.log(data);
        },
        async onInstrumentAcquisitionStarted({}, data) {
            console.log(data);
        },
        async onSampleFileCreated({ rootState, dispatch }, filename) {
            await dispatch('api/reloadDb', null, {root:true});
            await dispatch('getRecentAcquisitions');
            rootState.api.emit(
                'scenthound_process_samples',
                {
                    filename,
                    'sample_batch_id': rootState.batch.active.sample_batch_id
                }
            ); 
        },
    },
    getters: {}
}