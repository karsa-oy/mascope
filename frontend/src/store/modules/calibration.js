import { make } from 'vuex-pathify';

const state = {
    active: null,
    mzFit: null,
    mzFitStats: null,
};

export default {
    namespaced: true,
    state,
    mutations: {
        ...make.mutations(state),
    },
    actions: {
        async onCalibrationMzFitStats({ commit }, response) {
            let fit = response.fit;
            let fitStats = {
                post_mz: new Float32Array(response.stats.post_mz),
                post_dmz: new Float32Array(response.stats.post_dmz),
                pre_dmz_norm: response.stats.pre_dmz_norm,
                post_dmz_norm: response.stats.post_dmz_norm
            };
            await commit('SET_MZ_FIT', fit);
            await commit('SET_MZ_FIT_STATS', fitStats);
        },
    }
}