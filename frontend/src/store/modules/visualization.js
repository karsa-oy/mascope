import { commit, dispatch, make } from 'vuex-pathify';

const state = {
    // chart data
    tracesSignalTimeseries: null,
    tracesSignalSumSpectrum: null,
};

export default {
    namespaced: true,
    state,
    mutations: {
        ...make.mutations(state),
    },
    actions: {
        async reset({ commit }) {
            await commit('SET_TRACES_SIGNAL_SUM_SPECTRUM', null)
            await commit('SET_TRACES_SIGNAL_TIMESERIES', null)
        },
        async onVisualizationSignalSumSpectrum({ state, commit }, traces) {
            for (let trace of traces) {
                trace.x = new Float32Array(trace.x);
                trace.y = new Float32Array(trace.y);
            }
            const existingTraces = state.tracesSignalSumSpectrum;
            if (existingTraces) traces = [...existingTraces, ...traces];
            await commit('SET_TRACES_SIGNAL_SUM_SPECTRUM', traces);
        },
        async onVisualizationSignalTimeseries({ commit }, traces) {
            for (let trace of traces) {
                trace.x = new Float32Array(trace.x);
                trace.y = new Float32Array(trace.y);
            }
            const existingTraces = state.tracesSignalTimeseries;
            if (existingTraces) traces = [...existingTraces, ...traces];
            await commit('SET_TRACES_SIGNAL_TIMESERIES', traces);
        },
    },
}