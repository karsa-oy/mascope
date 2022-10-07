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
        async unload({ commit }) {
            await commit('SET_MZ_FIT', null);
            await commit('SET_MZ_FIT_STATS', null);
        },
        async onCalibrationMzFitStats({ commit }, response) {
            let fit = response.fit;
            let fitStats = response.stats;
            await commit('SET_MZ_FIT', fit);
            await commit('SET_MZ_FIT_STATS', fitStats);
        },
    }
}