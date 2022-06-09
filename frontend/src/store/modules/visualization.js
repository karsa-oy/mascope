export default {
    namespaced: true,
    state: {
        // chart data
        tracesProfile: [],
        tracesSpectrum: [],
        // api
        $ionFocusResponse: null,
        $ionFocusRequest: null,
    },
    mutations: {
        // Visualization
        SET_TRACES_PROFILE(state, data) {
            state.tracesProfile = data;
        },
        SET_TRACES_SPECTRUM(state, data) {
            state.tracesSpectrum = data;
        },
        REQUEST_ION_FOCUS(state, { sampleItemId, filename, parameters }) {
            state.$ionFocusRequest = {
                sampleItemId,
                filename,
                ...parameters
            }
        },
    },
    actions: {
        focusIon({ rootGetters, getters, commit }) {
            if (!getters['readyToFocusIon']) return;
            let itemFocused = rootGetters['sample/item/focusedRow'];
            let targetFocused = rootGetters['target/ion/focusedRow'];
            let isotopesSelected = rootGetters['target/isotope/selectedRows'];
            let ionId = targetFocused.id;
            let mzs = isotopesSelected.filter(
                isotope => isotope.ionId == ionId
            ).map(isotope => isotope.mz);
            let relAbus = isotopesSelected.filter(
                isotope => isotope.ionId == ionId
            ).map(isotope => isotope.relAbu);
            let tRange = null;
            commit('REQUEST_ION_FOCUS', {
                sampleItemId: itemFocused.id,
                filename: itemFocused.filename,
                parameters: {
                    mzs,
                    relAbus,
                    tRange,
                }
            });
            // Clear existing traces
            commit('SET_TRACES_PROFILE', []);
            commit('SET_TRACES_SPECTRUM', []);
        },
        // responses
        handleIonFocusResponse({ state, commit }) {
            if (state.$ionFocusResponse.spectra) {
                let tracesSpectrum = state.tracesSpectrum;
                for (let trace of state.$ionFocusResponse.spectra) {
                    trace.x = new Float32Array(trace.x);
                    trace.y = new Float32Array(trace.y);
                    tracesSpectrum.push(trace);
                }
                commit('SET_TRACES_SPECTRUM', tracesSpectrum);
            }
            if (state.$ionFocusResponse.profiles) {
                let tracesProfile = state.tracesProfile;
                for (let trace of state.$ionFocusResponse.profiles) {
                    trace.x = new Float32Array(trace.x);
                    trace.y = new Float32Array(trace.y);
                    tracesProfile.push(trace);
                }
                commit('SET_TRACES_PROFILE', tracesProfile);
            }
        },
    },
    getters: {
        readyToFocusIon(state, getters, rootState, rootGetters) {
            if (rootGetters['sample/item/focusedRow'] &&
                rootGetters['target/ion/focusedRow'] &&
                rootGetters['target/isotope/selectedRows'].length
            ) {
                return true;
            }
            return false;
        },
    },
    watchers: {
        'sample/item/focusedRow': 'visualization/focusIon',
        'target/ion/focusedRow': 'visualization/focusIon',
        'visualization/$ionFocusResponse': 'visualization/handleIonFocusResponse',
    }
}