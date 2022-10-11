import { make } from 'vuex-pathify';

const state = {
    active: null,
    mzFit: null,
    mzFitStats: null,
    paramRefineWindow: 10,
    paramMatchScoreMin: 0.9,
};

export default {
    namespaced: true,
    state,
    mutations: {
        ...make.mutations(state),
    },
    actions: {
        async load({ commit }, sample) {
            // reset if previous calibration loaded
            if (state.active) {
                dispatch('unload');
            }
            const sampleItemId = sample.sample_item_id;
            await rootState.api.query(`--sql
                SELECT
                    mz_calibration
                FROM sample_file
                NATURAL LEFT JOIN sample_item
                WHERE sample_item_id == '${sampleItemId}'
            `).then((res) => {
                commit('SET_MZ_FIT', res[0].mz_calibration);
            });
        },
        async unload({ commit }) {
            await commit('SET_MZ_FIT', null);
            await commit('SET_MZ_FIT_STATS', null);
        },
        async onCalibrationMzApplied({ dispatch }, sample_item_id) {
            await dispatch('unload');
            await dispatch('api/reloadDb', null, {root:true})
                .then(() => dispatch("batch/reload", null, {root:true}));
        },
        async onCalibrationMzFitStats({ commit }, response) {
            let fit = response.fit;
            let fitStats = response.stats;
            await commit('SET_MZ_FIT', fit);
            await commit('SET_MZ_FIT_STATS', fitStats);
        },
    }
}