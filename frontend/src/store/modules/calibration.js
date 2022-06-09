export default {
    namespaced: true,
    state: {
        mzFit: null,
        mzFitStats: null,

        $mzApplyRequest: null,
        $mzApplyResponse: null,
        $mzFitRequest: null,
        $mzFitResponse: null,
    },
    mutations: {
        // mz calibration
        MZ_APPLY_REQUEST(state, requestObject) {
            state.$mzApplyRequest = requestObject;
        },
        MZ_FIT(state, fit) {
            state.mzFit = fit;
        },
        MZ_FIT_REQUEST(state, requestObject) {
            state.$mzFitRequest = requestObject;
        },
        MZ_FIT_STATS(state, fitStats) {
            state.mzFitStats = fitStats;
        },
    },
    actions: {
        calibrateItems: function ({ commit }, { items, fit }) {
            let requestObject = {
                filenames: items.map(item => item.filename),
                fit,
            };
            commit('MZ_APPLY_REQUEST', requestObject);
        },
        handleMzFitResponse: function ({ state, commit }) {
            let response = state.$mzFitResponse;
            let fit = response.fit;
            let fitStats = {
                fitMz: new Float32Array(response.stats.postMz),
                fitMzError: new Float32Array(response.stats.postDmz),
                preDmzNorm: response.stats.preDmzNorm,
                postDmzNorm: response.stats.postDmzNorm
            };
            commit('MZ_FIT', fit);
            commit('MZ_FIT_STATS', fitStats);
        },
    },
    watchers: {
        'calibration/$mzFitResponse': 'calibration/handleMzFitResponse',
    }
}