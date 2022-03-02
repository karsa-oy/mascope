import modal from './modal';
import key from './key';

export default {
    namespaced: true,
    state: {
        query: null
    },
    modules: {
        modal,
        key
    }
}