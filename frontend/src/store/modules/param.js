import { make } from 'vuex-pathify';

const state = {
    possibleMatchThreshold: .5,
    probableMatchThreshold: .9,
}
export default {
    namespaced: true,
    state,
    mutations: make.mutations(state),
    actions: {
    }
}